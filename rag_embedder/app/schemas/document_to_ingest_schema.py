
from pydantic import BaseModel
from typing import Any

class ChunkToIngest(BaseModel):
    id: str
    chunk: str
    embeded_text: list[float]
    metadatas: dict[str, Any]

class DocumentToIngest(BaseModel):
    chunks: list[ChunkToIngest]

class DocumentsToIngest(BaseModel):
    documents: list[DocumentToIngest]
