from app.domain.models.vector_store_model import RetrievedChunk, VectorMetadata
from app.services.retrieval_service import (
    retrieve_chunks,
    retrieve_document_chunks,
    select_relevant_chunks,
)


def _chunk(path: str, index: int, distance: float) -> RetrievedChunk:
    return RetrievedChunk(
        document=f"{path}-{index}",
        metadata=VectorMetadata(
            path=path,
            title=path.removesuffix(".md"),
            chunk_index=index,
        ),
        distance=distance,
    )


class FakeVectorStoreRepository:
    def __init__(self, chunks: list[RetrievedChunk]) -> None:
        self.chunks = chunks
        self.call_args: tuple[object, ...] | None = None

    def query_chunks(
        self, collection_name: str, query_embedding: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        self.call_args = (collection_name, query_embedding, top_k)
        return self.chunks

    def get_chunks_by_paths(
        self, collection_name: str, paths: list[str]
    ) -> list[RetrievedChunk]:
        self.call_args = (collection_name, paths)
        return self.chunks


def _config() -> dict:
    return {
        "collections": {
            "default": "configured-wiki",
            "evaluation": "configured-gold",
        },
        "retriever": {
            "top_k": 10,
            "minimum_similarity": 0.7,
            "minimum_number_of_chunks": 2,
        },
    }


def test_select_relevant_chunks_applies_threshold_sort_and_minimum() -> None:
    chunks = [
        _chunk("low.md", 0, 0.8),
        _chunk("best.md", 0, 0.1),
        _chunk("middle.md", 0, 0.5),
    ]

    result = select_relevant_chunks(chunks, 0.7, 2)

    assert [chunk.metadata.path for chunk in result] == ["best.md", "middle.md"]


def test_retrieve_chunks_uses_configured_collection_and_formats_results() -> None:
    repository = FakeVectorStoreRepository([_chunk("guide.md", 1, 0.2)])

    response = retrieve_chunks(_config(), [0.1, 0.2], repository)

    assert repository.call_args == ("configured-wiki", [0.1, 0.2], 10)
    assert response.chunks[0].id == "guide | guide.md | 1"
    assert response.chunks[0].similarity == 0.8


def test_retrieve_chunks_uses_evaluation_collection_when_requested() -> None:
    repository = FakeVectorStoreRepository([])

    retrieve_chunks(_config(), [0.1], repository, "evaluation")

    assert repository.call_args == ("configured-gold", [0.1], 10)


def test_retrieve_document_chunks_deduplicates_paths_and_orders_chunks() -> None:
    repository = FakeVectorStoreRepository(
        [
            _chunk("b.md", 1, 0.0),
            _chunk("a.md", 2, 0.0),
            _chunk("a.md", 0, 0.0),
        ]
    )

    response = retrieve_document_chunks(
        _config(),
        ["a.md", "b.md", "a.md"],
        repository,
    )

    assert repository.call_args == ("configured-wiki", ["a.md", "b.md"])
    assert [chunk.document for chunk in response.chunks] == [
        "a.md-0",
        "a.md-2",
        "b.md-1",
    ]


def test_retrieve_document_chunks_preserves_empty_paths_contract() -> None:
    repository = FakeVectorStoreRepository([])

    response = retrieve_document_chunks(_config(), [], repository)

    assert repository.call_args == ("configured-wiki", [])
    assert response.chunks == []
