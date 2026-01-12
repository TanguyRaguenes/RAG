from pydantic import BaseModel


class SavedItemBase(BaseModel):
    id: str
    path: str
    chunk: str
    text_preview: str


class SaveItemsResponseBase(BaseModel):
    collection_count_before: int
    collection_count_after: int
    saved_items: list[SavedItemBase]
