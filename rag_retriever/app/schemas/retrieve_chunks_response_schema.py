from pydantic import BaseModel

from app.schemas.vector_db_items_schema import VectorMetadataBase


class ChunkModelBase(BaseModel):
    id: str
    document: str
    metadata: VectorMetadataBase
    similarity: float


class RetrievedChunksModelBase(BaseModel):
    chunks: list[ChunkModelBase]
