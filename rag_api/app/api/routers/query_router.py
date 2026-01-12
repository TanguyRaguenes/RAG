import time

from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.schemas.llm_request_schema import LlmRequestBase
from app.schemas.llm_response_schema import LlmResponseBase
from app.services.ask_question_service import ask_question

router = APIRouter()


@router.post("/ask_question", response_model=LlmResponseBase)
async def ask_question_route(
    body: LlmRequestBase,
    config=Depends(get_config),
) -> LlmResponseBase:
    start = time.perf_counter()

    answer = await ask_question(body.question, config)

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"

    return LlmResponseBase(answer=answer, duration=duration)
