from typing import Any

from pydantic import BaseModel


class ChunkBase(BaseModel):
    id: str
    chunk: str
    embeded_text: list[float]
    metadatas: dict[str, Any]
