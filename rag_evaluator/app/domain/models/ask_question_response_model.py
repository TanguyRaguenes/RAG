from pydantic import BaseModel
from typing import Any

class AskQuestionResponseModel(BaseModel):
    llm_answer: str
    chunks:list[dict[str, Any]] 
    sources:list[str]
    