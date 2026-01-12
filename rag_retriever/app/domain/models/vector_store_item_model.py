
from pydantic import BaseModel
from typing import Any

class VectorStoreItemsBase(BaseModel):
    ids: list[str]
    documents: list[str]
    embeddings: list[list[float]]
    metadatas: list[dict[str, Any]]