from typing import Any

from pydantic import BaseModel


class AskQuestionResponseBase(BaseModel):
    interaction_id: int | None = None
    llm_response: str
    retrieved_chunks: list[dict[str, Any]]
    retrieved_documents: dict[str, int]
    model: str
    generated_prompt: list[dict[str, Any]]
    duration: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
