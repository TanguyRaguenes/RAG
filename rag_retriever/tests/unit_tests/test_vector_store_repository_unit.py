import pytest
from app.core.exceptions import RetrievalFormatException, VectorStoreException
from app.dal.repositories import vector_store_repository as repository_module
from app.dal.repositories.vector_store_repository import VectorStoreRepository
from app.domain.models.vector_store_model import VectorMetadata, VectorStoreBatch
from chromadb.errors import InternalError


class FakeCollection:
    def __init__(self) -> None:
        self.ids = ["old-id"]
        self.upsert_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.get_calls: list[dict] = []
        self.query_calls: list[dict] = []

    def count(self) -> int:
        return len(self.ids)

    def upsert(self, **kwargs: object) -> None:
        self.upsert_calls.append(kwargs)

    def delete(self, **kwargs: object) -> None:
        self.delete_calls.append(kwargs)

    def get(self, **kwargs: object) -> dict:
        self.get_calls.append(kwargs)
        if "ids" in kwargs:
            return {
                "ids": ["new-id"],
                "documents": ["document"],
                "metadatas": [_metadata()],
            }
        if "where" in kwargs:
            return {
                "documents": ["second", "first"],
                "metadatas": [
                    _metadata(path="doc.md", chunk_index=1),
                    _metadata(path="doc.md", chunk_index=0),
                ],
            }
        return {"ids": self.ids}

    def query(self, **kwargs: object) -> dict:
        self.query_calls.append(kwargs)
        return {
            "documents": [["best", "second"]],
            "metadatas": [[_metadata(), _metadata(path="second.md")]],
            "distances": [[0.1, 0.4]],
        }


class FakeChromaClient:
    def __init__(self, collection: FakeCollection | None = None) -> None:
        self.collection = collection or FakeCollection()
        self.get_or_create_calls: list[dict] = []
        self.delete_calls: list[dict] = []

    def get_or_create_collection(self, **kwargs: object) -> FakeCollection:
        self.get_or_create_calls.append(kwargs)
        return self.collection

    def delete_collection(self, **kwargs: object) -> None:
        self.delete_calls.append(kwargs)


def _metadata(
    *, path: str = "doc.md", chunk_index: int = 0
) -> dict[str, str | int | bool]:
    return {
        "path": path,
        "title": "Doc",
        "chunk_index": chunk_index,
        "related_links": "",
        "has_links": False,
    }


def _repository(collection: FakeCollection | None = None) -> VectorStoreRepository:
    repository = VectorStoreRepository.__new__(VectorStoreRepository)
    repository._client = FakeChromaClient(collection)
    return repository


def test_repository_initializes_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    clients: list[tuple[str, int]] = []

    def fake_http_client(host: str, port: int) -> FakeChromaClient:
        clients.append((host, port))
        return FakeChromaClient()

    monkeypatch.setattr(repository_module.chromadb, "HttpClient", fake_http_client)

    VectorStoreRepository("localhost", 8123)

    assert clients == [("localhost", 8123)]


def test_repository_translates_known_client_construction_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_http_client(host: str, port: int) -> FakeChromaClient:
        raise InternalError("internal endpoint unavailable")

    monkeypatch.setattr(repository_module.chromadb, "HttpClient", failing_http_client)

    with pytest.raises(VectorStoreException) as exc_info:
        VectorStoreRepository("internal-host", 8123)

    assert exc_info.value.internal_details == {
        "operation": "create_client",
        "error_type": "InternalError",
    }
    assert "internal-host" not in str(exc_info.value.to_dict())


def test_repository_upserts_domain_batch_in_named_collection() -> None:
    collection = FakeCollection()
    repository = _repository(collection)
    batch = VectorStoreBatch(
        ids=["new-id"],
        documents=["document"],
        embeddings=[[0.1, 0.2]],
        metadatas=[VectorMetadata(path="doc.md", title="Doc", chunk_index=0)],
    )

    repository.upsert_items("configured-wiki", batch)

    assert repository._client.get_or_create_calls[0]["name"] == "configured-wiki"
    assert collection.upsert_calls == [
        {
            "ids": ["new-id"],
            "documents": ["document"],
            "embeddings": [[0.1, 0.2]],
            "metadatas": [_metadata()],
        }
    ]


def test_repository_maps_storage_payloads_to_domain_models() -> None:
    repository = _repository()

    saved = repository.get_items("wiki", ["new-id"])
    queried = repository.query_chunks("wiki", [0.1], 2)
    by_path = repository.get_chunks_by_paths("wiki", ["doc.md"])

    assert saved[0].metadata.path == "doc.md"
    assert queried[0].similarity == 0.9
    assert by_path[1].metadata.chunk_index == 0


def test_repository_queries_multiple_paths_with_single_chroma_filter() -> None:
    collection = FakeCollection()
    repository = _repository(collection)

    repository.get_chunks_by_paths("wiki", ["a.md", "b.md"])

    assert collection.get_calls[-1]["where"] == {"path": {"$in": ["a.md", "b.md"]}}


def test_repository_rejects_misaligned_chroma_query_payload() -> None:
    class InvalidCollection(FakeCollection):
        def query(self, **kwargs: object) -> dict:
            return {
                "documents": [["document"]],
                "metadatas": [[_metadata()]],
                "distances": [[]],
            }

    with pytest.raises(RetrievalFormatException) as exc_info:
        _repository(InvalidCollection()).query_chunks("wiki", [0.1], 2)

    assert exc_info.value.internal_details == {"operation": "query"}


def test_repository_rejects_malformed_metadata_as_format_error() -> None:
    class InvalidCollection(FakeCollection):
        def query(self, **kwargs: object) -> dict:
            return {
                "documents": [["document"]],
                "metadatas": [[{"path": "doc.md", "title": "Doc"}]],
                "distances": [[0.1]],
            }

    with pytest.raises(RetrievalFormatException) as exc_info:
        _repository(InvalidCollection()).query_chunks("wiki", [0.1], 2)

    assert exc_info.value.internal_details == {"operation": "query"}


def test_repository_wraps_chroma_failures() -> None:
    class FailingCollection(FakeCollection):
        def count(self) -> int:
            raise InternalError("chroma unavailable")

    with pytest.raises(VectorStoreException) as exc_info:
        _repository(FailingCollection()).count_items("wiki")

    assert exc_info.value.internal_details == {
        "operation": "count",
        "error_type": "InternalError",
    }


def test_repository_does_not_misclassify_unexpected_errors_as_chroma() -> None:
    class FailingCollection(FakeCollection):
        def count(self) -> int:
            raise RuntimeError("programming failure")

    with pytest.raises(RuntimeError, match="programming failure"):
        _repository(FailingCollection()).count_items("wiki")


def test_repository_resets_collection_without_exposing_collection_object() -> None:
    repository = _repository()

    repository.reset_collection("wiki")

    assert repository._client.delete_calls == [{"name": "wiki"}]
    assert repository._client.get_or_create_calls[-1]["name"] == "wiki"
