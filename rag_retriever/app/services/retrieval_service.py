from typing import Any

from app.schemas.retrieve_chunks_response_schema import (
    ChunkModelBase,
    RetrievedChunksModelBase,
)


def retrieve_chunks(
    config, collection, embeded_question: list[float], vector_store_repository
) -> RetrievedChunksModelBase:
    top_k: int = config["retriever"]["top_k"]
    minimum_similarity: float = config["retriever"]["minimum_similarity"]
    minimum_number_of_chunks: int = config["retriever"]["minimum_number_of_chunks"]

    retrieved_chunks: list[dict[str, Any]] = (
        vector_store_repository.retrieve_chunks_filtered(
            collection,
            embeded_question,
            top_k,
            minimum_similarity,
            minimum_number_of_chunks,
        )
    )

    formatted_chunks: list[ChunkModelBase] = []

    for chunk in retrieved_chunks:
        formatted_chunk = ChunkModelBase(
            id=f"{chunk['metadata']['title']} | {chunk['metadata']['path']} | {chunk['metadata']['chunk_index']}",
            document=chunk["document"],
            metadata=chunk["metadata"],
            similarity=round(chunk["similarity"], 3),
        )
        formatted_chunks.append(formatted_chunk)

    return RetrievedChunksModelBase(chunks=formatted_chunks)
