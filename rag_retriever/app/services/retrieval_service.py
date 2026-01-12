from typing import Any

from app.schemas.retrieve_chunks_response_schema import (
    ChunkModelBase,
    RetrievedChunksModelBase,
)


def retrieve_chunks(
    config, collection, embeded_question: list[float], vector_store_repository
) -> RetrievedChunksModelBase:
    top_k: int = config["retriever"]["top_k"]

    response: list[dict[str, Any]] = vector_store_repository.retrieve_chunks(
        collection, embeded_question, top_k
    )

    chunks = []
    ids = response["ids"][0]
    docs = response["documents"][0]
    metas = response["metadatas"][0]

    for id, document, metadata in zip(ids, docs, metas):
        retrieved_chunk = ChunkModelBase(id=id, document=document, metadata=metadata)
        chunks.append(retrieved_chunk)

    return RetrievedChunksModelBase(chunks=chunks)
