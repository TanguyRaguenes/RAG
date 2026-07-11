from typing import Any

from app.dal.clients.embedder_client import embed_question
from app.dal.clients.reranker_client import rerank_chunks as rerank_chunks_client
from app.dal.clients.retriever_client import retrieve_chunks as retrieve_chunks_client
from app.schemas.retrieve_chunks_response_schema import (
    RetrieveChunksResponseBase,
)


async def retrieve_chunks(question: str, config: dict) -> RetrieveChunksResponseBase:
    reranked_chunks = await retrieve_and_rerank_chunks(question)

    return RetrieveChunksResponseBase(
        retrieved_chunks=reranked_chunks,
    )


async def retrieve_and_rerank_chunks(question: str) -> list[dict[str, Any]]:
    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks_client(
        embeded_question
    )

    reranked_chunks: list[dict[str, Any]] = await rerank_chunks_client(
        question,
        retrieved_chunks,
    )

    return reranked_chunks
