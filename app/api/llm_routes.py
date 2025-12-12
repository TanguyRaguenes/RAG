from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.bl.llm_client import OllamaClient

router = APIRouter(tags=["llm"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str


@router.post("/ask", response_model=AskResponse)
async def ask_llm(payload: AskRequest) -> AskResponse:
    client = OllamaClient()
    answer = await client.chat(payload.question)
    return AskResponse(answer=answer)
