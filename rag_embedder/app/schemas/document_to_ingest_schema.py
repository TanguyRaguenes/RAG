from pydantic import BaseModel

from app.schemas.vector_store_items_schema import VectorMetadataBase


class ChunkToIngest(BaseModel):
    id: str
    chunk: str
    embeded_text: list[float]
    metadatas: VectorMetadataBase


class DocumentToIngest(BaseModel):
    chunks: list[ChunkToIngest]


class DocumentsToIngest(BaseModel):
    documents: list[DocumentToIngest]
