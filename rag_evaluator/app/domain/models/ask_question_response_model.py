from typing import Any
from pydantic import BaseModel

class AskQuestionResponseBase(BaseModel):
    llm_response: str
    retrieved_chunks: list[dict[str, Any]]
    retrieved_documents: dict[str, int]
    model: str
    generated_prompt: list[dict[str, Any]]
    duration: str
