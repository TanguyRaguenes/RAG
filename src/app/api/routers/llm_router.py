import time

from fastapi import APIRouter, Request
from src.app.services.llm_service import ask_question
from src.app.schemas.llm_request_schema import llmRequestBase
from src.app.schemas.llm_response_schema import llmResponseBase

router = APIRouter()

@router.post("/ask", response_model=llmResponseBase)
async def ask_question_route(request: Request, body: llmRequestBase) -> llmResponseBase:

    start = time.perf_counter()

    config = request.app.state.config

    answer = await ask_question(body.question, config)

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"
    
    return llmResponseBase(answer=answer, duration=duration)
