from pydantic import BaseModel
from typing import List, Optional


class IngestedItem(BaseModel):
    id: str
    path: Optional[str] = None
    chunk: Optional[int] = None
    text_preview: str

class IngestResponseBase(BaseModel):
    answer: str
    collection_count_before: int
    collection_count_after: int
    written_items: List[IngestedItem]
    duration: str