from typing import Any

from app.services.retrieval_service import (
    format_retrieved_chunk,
    retrieve_chunks,
    retrieve_document_chunks,
)


class FakeVectorStoreRepository:
    def __init__(self, chunks: list[dict[str, Any]]):
        self.chunks = chunks
        self.call_args = None

    def retrieve_chunks_filtered(
        self,
        collection: object,
        query_embedding: list[float],
        top_k: int,
        minimum_similarity: float,
        minimum_number_of_chunks: int,
    ) -> list[dict[str, Any]]:
        self.call_args = (
            collection,
            query_embedding,
            top_k,
            minimum_similarity,
            minimum_number_of_chunks,
        )
        return self.chunks

    def retrieve_document_chunks_by_paths(
        self,
        collection: object,
        paths: list[str],
    ) -> list[dict[str, Any]]:
        self.call_args = (collection, paths)
        return self.chunks


def test_format_retrieved_chunk_builds_public_chunk_model() -> None:
    chunk = {
        "document": "contenu",
        "metadata": {
            "title": "Titre",
            "path": "wiki/page.md",
            "chunk_index": 3,
        },
        "similarity": 0.87654,
    }

    result = format_retrieved_chunk(chunk)

    assert result.id == "Titre | wiki/page.md | 3"
    assert result.document == "contenu"
    assert result.similarity == 0.877


def test_retrieve_chunks_uses_config_and_formats_repository_results() -> None:
    collection = object()
    repository = FakeVectorStoreRepository(
        [
            {
                "document": "contenu",
                "metadata": {
                    "title": "Titre",
                    "path": "wiki/page.md",
                    "chunk_index": 1,
                },
                "similarity": 0.75,
            }
        ]
    )
    config = {
        "retriever": {
            "top_k": 10,
            "minimum_similarity": 0.5,
            "minimum_number_of_chunks": 2,
            "max_related_links": 3,
        }
    }

    response = retrieve_chunks(config, collection, [0.1, 0.2], repository)

    assert repository.call_args == (collection, [0.1, 0.2], 10, 0.5, 2)
    assert len(response.chunks) == 1
    assert response.chunks[0].id == "Titre | wiki/page.md | 1"


def test_retrieve_chunks_returns_empty_response_when_repository_returns_no_chunks() -> None:
    repository = FakeVectorStoreRepository([])
    config = {
        "retriever": {
            "top_k": 10,
            "minimum_similarity": 0.5,
            "minimum_number_of_chunks": 2,
            "max_related_links": 3,
        }
    }

    response = retrieve_chunks(config, object(), [0.1], repository)

    assert response.chunks == []


def test_retrieve_document_chunks_formats_repository_results() -> None:
    collection = object()
    paths = ["wiki/page.md"]
    repository = FakeVectorStoreRepository(
        [
            {
                "document": "document chunk",
                "metadata": {
                    "title": "Titre",
                    "path": "wiki/page.md",
                    "chunk_index": 1,
                },
                "similarity": 0.75,
            }
        ]
    )

    response = retrieve_document_chunks(collection, paths, repository)

    assert repository.call_args == (collection, paths)
    assert response.chunks[0].document == "document chunk"


def test_format_retrieved_chunk_raises_key_error_when_required_metadata_is_missing() -> None:
    chunk = {
        "document": "contenu",
        "metadata": {"title": "Titre", "path": "wiki/page.md"},
        "similarity": 0.8,
    }

    try:
        format_retrieved_chunk(chunk)
    except KeyError as exc:
        assert exc.args == ("chunk_index",)
    else:
        raise AssertionError("format_retrieved_chunk should require chunk_index metadata")
