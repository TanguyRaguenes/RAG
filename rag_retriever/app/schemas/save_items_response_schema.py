from pydantic import BaseModel

from app.schemas.vector_db_items_schema import VectorMetadataBase


class SavedItemBase(BaseModel):
    id: str
    chunk: str
    metadatas: VectorMetadataBase


class SaveItemsResponseBase(BaseModel):
    collection_count_before: int
    collection_count_after: int
    saved_items: list[SavedItemBase]
