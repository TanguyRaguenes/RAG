from typing import Any

from app.dal.clients.embedder_client import embed_question
from app.dal.clients.retriever_client import retrieve_chunks as retrieve_chunks_client
from app.schemas.retrieve_chunks_response_schema import (
    RetrieveChunksResponseBase,
)


async def retrieve_chunks(question: str, config: dict) -> RetrieveChunksResponseBase:
    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks_client(
        embeded_question
    )

    return RetrieveChunksResponseBase(
        retrieved_chunks=retrieved_chunks,
    )
