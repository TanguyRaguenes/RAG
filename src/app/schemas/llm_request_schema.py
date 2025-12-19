
from pydantic import BaseModel

class llmRequestBase(BaseModel):
    question: str