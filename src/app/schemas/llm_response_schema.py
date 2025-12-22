
from pydantic import BaseModel

class LlmResponseBase(BaseModel):
    answer: str
    duration: str