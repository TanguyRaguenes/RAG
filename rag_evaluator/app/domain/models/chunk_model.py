from pydantic import BaseModel
from typing import Any

class ChunkBase(BaseModel):
    id: str
    chunk: str
    embeded_text: list[float]
    metadatas: dict[str, Any]