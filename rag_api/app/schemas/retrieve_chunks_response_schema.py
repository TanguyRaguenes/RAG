from typing import Any

from pydantic import BaseModel


class RetrieveChunksResponseBase(BaseModel):
    retrieved_chunks: list[dict[str, Any]]
