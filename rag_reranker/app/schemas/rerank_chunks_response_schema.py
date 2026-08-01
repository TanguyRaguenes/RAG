from typing import Any

from pydantic import BaseModel, FiniteFloat


class RerankedChunkModelBase(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    similarity: FiniteFloat
    rerank_score: FiniteFloat


class RerankChunksResponseBase(BaseModel):
    duration_ms: float
    duration_human: str
    reranked_chunks: list[RerankedChunkModelBase]
