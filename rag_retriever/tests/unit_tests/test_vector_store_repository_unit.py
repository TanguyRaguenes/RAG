import pytest

from app.core.exceptions import VectorStoreException
from app.dal.repositories import vector_store_repository as repository_module
from app.dal.repositories.vector_store_repository import (
    VectorStoreRepository,
    build_enriched_chunks,
    extract_related_links,
    filter_by_similarity,
    sort_chunks_by_index,
)
from app.schemas.vector_db_items_schema import VectorStoreItemsBase


def test_build_enriched_chunks_calculates_cosine_similarity() -> None:
    chunks = build_enriched_chunks(
        documents=["doc-a", "doc-b"],
        metadatas=[{"path": "a"}, {"path": "b"}],
        distances=[0.2, 0.8],
    )

    assert chunks == [
        {
            "document": "doc-a",
            "metadata": {"path": "a"},
            "distance": 0.2,
            "similarity": 0.8,
        },
        {
            "document": "doc-b",
            "metadata": {"path": "b"},
            "distance": 0.8,
            "similarity": 0.19999999999999996,
        },
    ]


def test_filter_by_similarity_keeps_best_chunks_sorted() -> None:
    chunks = [
        {"document": "low", "metadata": {}, "similarity": 0.2},
        {"document": "high", "metadata": {}, "similarity": 0.9},
        {"document": "mid", "metadata": {}, "similarity": 0.7},
    ]

    result = filter_by_similarity(chunks, minimum_similarity=0.5)

    assert [chunk["document"] for chunk in result] == ["high", "mid"]


def test_extract_related_links_keeps_highest_parent_score() -> None:
    chunks = [
        {
            "metadata": {
                "has_links": True,
                "related_links": "wiki/a.md, wiki/b.md",
            },
            "similarity": 0.6,
        },
        {
            "metadata": {
                "has_links": True,
                "related_links": "wiki/a.md",
            },
            "similarity": 0.9,
        },
        {
            "metadata": {
                "has_links": False,
                "related_links": "wiki/c.md",
            },
            "similarity": 1.0,
        },
    ]

    assert extract_related_links(chunks) == {
        "wiki/a.md": 0.9,
        "wiki/b.md": 0.6,
    }


def test_sort_chunks_by_index_orders_document_chunks() -> None:
    result = sort_chunks_by_index(
        [
            {
                "document": "B",
                "metadata": {"path": "doc.md", "title": "Doc", "chunk_index": 2},
                "similarity": 1.0,
            },
            {
                "document": "A",
                "metadata": {"path": "doc.md", "title": "Doc", "chunk_index": 1},
                "similarity": 1.0,
            },
        ],
    )

    assert [chunk["document"] for chunk in result] == ["A", "B"]


class FakeCollection:
    def __init__(self):
        self.upsert_calls = []
        self.delete_calls = []
        self.get_calls = []
        self.query_payload = {
            "documents": [["doc-a", "doc-b"]],
            "metadatas": [
                [
                    {
                        "path": "a.md",
                        "title": "A",
                        "chunk_index": 0,
                        "has_links": True,
                        "related_links": "b.md",
                    },
                    {
                        "path": "b.md",
                        "title": "B",
                        "chunk_index": 0,
                        "has_links": False,
                        "related_links": "",
                    },
                ]
            ],
            "distances": [[0.1, 0.6]],
        }

    def upsert(self, **kwargs):
        self.upsert_calls.append(kwargs)

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        if kwargs.get("where"):
            return {
                "documents": [
                    "CONTEXT : Guide > API\nCONTENT : A",
                    "CONTEXT : Guide > API\nCONTENT : B",
                    "CONTEXT : Guide > CLI\nCONTENT : C",
                ],
                "metadatas": [
                    {"path": "a.md", "title": "A", "chunk_index": 0},
                    {"path": "a.md", "title": "A", "chunk_index": 1},
                    {"path": "a.md", "title": "A", "chunk_index": 2},
                ],
            }
        if kwargs:
            return {
                "ids": ["id"],
                "documents": ["doc"],
                "metadatas": [{"path": "doc.md"}],
            }
        return {"ids": ["id"]}

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)

    def query(self, **kwargs):
        self.query_call = kwargs
        return self.query_payload


class FailingCollection:
    def __init__(self, failure: Exception | None = None):
        self.failure = failure or RuntimeError("chroma unavailable")

    def upsert(self, **kwargs):
        raise self.failure

    def get(self, **kwargs):
        raise self.failure

    def delete(self, **kwargs):
        raise self.failure

    def query(self, **kwargs):
        raise self.failure


class FakeChromaClient:
    def __init__(self):
        self.get_or_create_calls = []
        self.delete_calls = []

    def get_or_create_collection(self, **kwargs):
        self.get_or_create_calls.append(kwargs)
        return "collection"

    def delete_collection(self, **kwargs):
        self.delete_calls.append(kwargs)


def _repository() -> VectorStoreRepository:
    repository = VectorStoreRepository.__new__(VectorStoreRepository)
    repository.config = {}
    return repository


def test_repository_initializes_http_client_and_creates_cosine_collection(
    monkeypatch,
) -> None:
    clients = []

    def fake_http_client(host: str, port: int):
        client = FakeChromaClient()
        clients.append((host, port, client))
        return client

    monkeypatch.setattr(repository_module.chromadb, "HttpClient", fake_http_client)

    repository = VectorStoreRepository(
        {"collection": {"name": "wiki"}}, "localhost", 8123
    )
    collection = repository.get_or_create_collection("wiki")

    assert collection == "collection"
    assert repository.config == {"collection": {"name": "wiki"}}
    assert clients[0][:2] == ("localhost", 8123)
    assert clients[0][2].get_or_create_calls == [
        {"name": "wiki", "configuration": {"hnsw": {"space": "cosine"}}}
    ]


def test_get_or_create_collection_wraps_chroma_error(monkeypatch) -> None:
    class FailingClient:
        def get_or_create_collection(self, **kwargs):
            raise RuntimeError("boom")

    def fake_http_client(host: str, port: int):
        return FailingClient()

    monkeypatch.setattr(repository_module.chromadb, "HttpClient", fake_http_client)
    repository = VectorStoreRepository({}, "localhost", 8123)

    with pytest.raises(VectorStoreException) as exception_info:
        repository.get_or_create_collection("wiki")

    assert exception_info.value.details == {"collection": "wiki"}


def test_insert_or_update_items_in_collection_upserts_all_fields() -> None:
    collection = FakeCollection()
    items = VectorStoreItemsBase(
        ids=["id"],
        documents=["doc"],
        embeddings=[[0.1]],
        metadatas=[{"path": "doc.md"}],
    )

    _repository().insert_or_update_items_in_collection(collection, items)

    assert collection.upsert_calls == [
        {
            "ids": ["id"],
            "documents": ["doc"],
            "embeddings": [[0.1]],
            "metadatas": [{"path": "doc.md"}],
        }
    ]


def test_insert_or_update_items_in_collection_wraps_chroma_error() -> None:
    items = VectorStoreItemsBase(
        ids=["id"],
        documents=["doc"],
        embeddings=[[0.1]],
        metadatas=[{"path": "doc.md"}],
    )

    with pytest.raises(VectorStoreException) as exception_info:
        _repository().insert_or_update_items_in_collection(FailingCollection(), items)

    assert exception_info.value.details == {"item_count": 1}


def test_get_collection_items_maps_chroma_payload_to_saved_items() -> None:
    items = _repository().get_collection_items(
        FakeCollection(), ["id"], ["documents", "metadatas"]
    )

    assert items[0].id == "id"
    assert items[0].chunk == "doc"
    assert items[0].metadatas == {"path": "doc.md"}


def test_get_collection_items_wraps_chroma_error() -> None:
    with pytest.raises(VectorStoreException) as exception_info:
        _repository().get_collection_items(
            FailingCollection(), ["id-1", "id-2"], ["documents"]
        )

    assert exception_info.value.details == {"item_count": 2}


def test_delete_collection_by_name_delegates_to_client() -> None:
    repository = _repository()
    repository.client = FakeChromaClient()

    repository.delete_collection_by_name("wiki")

    assert repository.client.delete_calls == [{"name": "wiki"}]


def test_delete_collection_by_name_wraps_chroma_error() -> None:
    class FailingClient:
        def delete_collection(self, **kwargs):
            raise RuntimeError("boom")

    repository = _repository()
    repository.client = FailingClient()

    with pytest.raises(VectorStoreException) as exception_info:
        repository.delete_collection_by_name("wiki")

    assert exception_info.value.details == {"collection": "wiki"}


def test_delete_items_by_ids_ignores_empty_list_and_deletes_non_empty_list() -> None:
    collection = FakeCollection()
    repository = _repository()

    repository.delete_items_by_ids(collection, [])
    repository.delete_items_by_ids(collection, ["id"])

    assert collection.delete_calls == [{"ids": ["id"]}]


def test_delete_items_by_ids_wraps_chroma_error() -> None:
    with pytest.raises(VectorStoreException) as exception_info:
        _repository().delete_items_by_ids(FailingCollection(), ["id"])

    assert exception_info.value.details == {"item_count": 1}


def test_delete_all_items_deletes_existing_ids() -> None:
    collection = FakeCollection()

    _repository().delete_all_items(collection)

    assert collection.delete_calls == [{"ids": ["id"]}]


def test_retrieve_chunks_returns_raw_chroma_response() -> None:
    collection = FakeCollection()

    result = _repository().retrieve_chunks(collection, [0.1], 3)

    assert result == collection.query_payload
    assert collection.query_call == {
        "query_embeddings": [[0.1]],
        "n_results": 3,
        "include": ["documents", "metadatas"],
    }


def test_retrieve_chunks_wraps_chroma_error() -> None:
    with pytest.raises(VectorStoreException) as exception_info:
        _repository().retrieve_chunks(FailingCollection(), [0.1], 3)

    assert exception_info.value.details == {"top_k": 3}


def test_retrieve_chunks_filtered_filters_and_does_not_add_related_chunks() -> None:
    collection = FakeCollection()

    result = _repository().retrieve_chunks_filtered(
        collection,
        query_embedding=[0.1],
        top_k=2,
        minimum_similarity=0.95,
        minimum_number_of_chunks=1,
    )

    assert result[0]["document"] == "doc-a"
    assert result[0]["similarity"] == 0.9
    assert len(result) == 1
    assert collection.query_call["include"] == ["documents", "metadatas", "distances"]


def test_retrieve_chunks_filtered_wraps_chroma_error() -> None:
    with pytest.raises(VectorStoreException) as exception_info:
        _repository().retrieve_chunks_filtered(FailingCollection(), [0.1], 3, 0.8, 1)

    assert exception_info.value.details == {"top_k": 3, "minimum_similarity": 0.8}


def test_retrieve_document_chunks_by_paths_deduplicates_paths_and_sorts_chunks() -> (
    None
):
    collection = FakeCollection()

    result = _repository().retrieve_document_chunks_by_paths(
        collection,
        ["a.md", "a.md"],
    )

    assert [chunk["metadata"]["chunk_index"] for chunk in result] == [0, 1, 2]
    assert [call["where"] for call in collection.get_calls] == [{"path": "a.md"}]


def test_retrieve_document_chunks_by_paths_wraps_chroma_error() -> None:
    with pytest.raises(VectorStoreException) as exception_info:
        _repository().retrieve_document_chunks_by_paths(FailingCollection(), ["a.md"])

    assert exception_info.value.details == {"path": "a.md"}


def test_retrieve_related_chunks_adds_non_duplicate_linked_documents() -> None:
    class RelatedCollection:
        def get(self, **kwargs):
            return {
                "documents": ["linked content"],
                "metadatas": [
                    {"path": "linked.md", "title": "Linked", "chunk_index": 0}
                ],
            }

    chunks = [
        {
            "document": "source content",
            "metadata": {"has_links": True, "related_links": "linked.md"},
            "distance": 0.1,
            "similarity": 0.9,
        }
    ]

    result = _repository().retrieve_related_chunks(chunks, RelatedCollection(), 1)

    assert len(result) == 2
    assert result[1] == {
        "document": "CONTEXTE : DOCUMENT LIÉ (Détail)\nlinked content",
        "metadata": {"path": "linked.md", "title": "Linked", "chunk_index": 0},
        "distance": 0.0,
        "similarity": 0.9,
    }


def test_build_enriched_chunks_and_filter_by_similarity_sort_results() -> None:
    chunks = build_enriched_chunks(
        ["low", "high"],
        [{"path": "low"}, {"path": "high"}],
        [0.7, 0.1],
    )

    result = filter_by_similarity(chunks, 0.5)

    assert [chunk["document"] for chunk in result] == ["high"]
    assert result[0]["similarity"] == 0.9


def test_extract_related_links_keeps_best_score_and_ignores_empty_links() -> None:
    result = extract_related_links(
        [
            {
                "metadata": {"has_links": True, "related_links": " a.md, "},
                "similarity": 0.6,
            },
            {
                "metadata": {"has_links": True, "related_links": "a.md,b.md"},
                "similarity": 0.9,
            },
            {
                "metadata": {"has_links": False, "related_links": "c.md"},
                "similarity": 1.0,
            },
        ]
    )

    assert result == {"a.md": 0.9, "b.md": 0.9}
