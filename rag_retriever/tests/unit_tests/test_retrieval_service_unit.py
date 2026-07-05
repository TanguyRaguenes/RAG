from typing import Any

from app.services.retrieval_service import format_retrieved_chunk, retrieve_chunks


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
        max_related_links: int,
    ) -> list[dict[str, Any]]:
        self.call_args = (
            collection,
            query_embedding,
            top_k,
            minimum_similarity,
            minimum_number_of_chunks,
            max_related_links,
        )
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

    assert repository.call_args == (collection, [0.1, 0.2], 10, 0.5, 2, 3)
    assert len(response.chunks) == 1
    assert response.chunks[0].id == "Titre | wiki/page.md | 1"
