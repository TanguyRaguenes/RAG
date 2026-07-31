from typing import Any

from pydantic import BaseModel


class VectorStoreItemsBase(BaseModel):
    ids: list[str]
    documents: list[str]
    embeddings: list[list[float]]
    metadatas: list[dict[str, Any]]
