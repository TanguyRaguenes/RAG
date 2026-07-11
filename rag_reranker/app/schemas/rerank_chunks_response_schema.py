from typing import Any

from pydantic import BaseModel


class RerankedChunkModelBase(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    similarity: float
    rerank_score: float


class RerankChunksResponseBase(BaseModel):
    duration_ms: float
    duration_human: str
    reranked_chunks: list[RerankedChunkModelBase]
