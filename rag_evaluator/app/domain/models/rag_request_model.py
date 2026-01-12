
from pydantic import BaseModel

class RagRequestBase(BaseModel):
    question: str