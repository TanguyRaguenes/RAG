
from pydantic import BaseModel

class llmResponseBase(BaseModel):
    answer: str
    duration:str