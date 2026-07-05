from typing import Any

from app.schemas.retrieve_chunks_response_schema import (
    ChunkModelBase,
    RetrievedChunksModelBase,
)


def retrieve_chunks(
    config: dict[str, Any], collection, embeded_question: list[float], vector_store_repository
) -> RetrievedChunksModelBase:
    top_k: int = config["retriever"]["top_k"]
    minimum_similarity: float = config["retriever"]["minimum_similarity"]
    minimum_number_of_chunks: int = config["retriever"]["minimum_number_of_chunks"]
    max_related_links: int = config["retriever"]["max_related_links"]

    retrieved_chunks: list[dict[str, Any]] = (
        vector_store_repository.retrieve_chunks_filtered(
            collection,
            embeded_question,
            top_k,
            minimum_similarity,
            minimum_number_of_chunks,
            max_related_links,
        )
    )

    return RetrievedChunksModelBase(
        chunks=[format_retrieved_chunk(chunk) for chunk in retrieved_chunks]
    )


def format_retrieved_chunk(chunk: dict[str, Any]) -> ChunkModelBase:
    metadata = chunk["metadata"]

    return ChunkModelBase(
        id=_build_chunk_id(metadata),
        document=chunk["document"],
        metadata=metadata,
        similarity=round(chunk["similarity"], 3),
    )


def _build_chunk_id(metadata: dict[str, Any]) -> str:
    return f"{metadata['title']} | {metadata['path']} | {metadata['chunk_index']}"
