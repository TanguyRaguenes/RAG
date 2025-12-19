from pydantic import BaseModel
from typing import List


class EmbeddingItem(BaseModel):
    page_path: str
    embedding: List[float]

class embeddingResponseBase(BaseModel):
    answer: List[EmbeddingItem]
    duration:str