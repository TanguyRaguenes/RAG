from typing import Any

from pydantic import BaseModel


class ChunkModelBase(BaseModel):
    id: str
    document: str
    metadata: dict[str, Any]
    similarity: float


class RetrievedChunksModelBase(BaseModel):
    chunks: list[ChunkModelBase]
