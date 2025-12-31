from pydantic import BaseModel
from typing import Any

class AskQuestionResponseModel(BaseModel):
    llm_answer: str
    chuncks:list[dict[str, Any]] 
    sources:list[str]
    