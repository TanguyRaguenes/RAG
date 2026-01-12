from pydantic import BaseModel
from typing import Any

class AskQuestionResponseBase(BaseModel):
    llm_answer: str
    chunks:list[dict[str, Any]] 
    sources:list[str]
    