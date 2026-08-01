from typing import Any

from pydantic import BaseModel, Field, FiniteFloat


class ChunkModelBase(BaseModel):
    """Chunk candidat reçu par l'API de reranking."""

    id: str
    document: str
    metadata: dict[str, Any]
    similarity: FiniteFloat


class RerankChunksRequestBase(BaseModel):
    """Requête HTTP validée de reranking."""

    question: str = Field(min_length=1)
    chunks: list[ChunkModelBase]
