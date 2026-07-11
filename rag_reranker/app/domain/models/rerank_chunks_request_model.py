from typing import Any

from pydantic import BaseModel, Field


class ChunkModelBase(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    similarity: float


class RerankChunksRequestBase(BaseModel):
    question: str = Field(min_length=1)
    chunks: list[ChunkModelBase]
