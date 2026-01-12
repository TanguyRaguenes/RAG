
from pydantic import BaseModel

class LlmRequestBase(BaseModel):
    question: str