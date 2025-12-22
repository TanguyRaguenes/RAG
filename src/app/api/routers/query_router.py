import time

from fastapi import APIRouter, Request
from src.app.services.question_answering_service import ask_question
from src.app.schemas.llm_request_schema import LlmRequestBase
from src.app.schemas.llm_response_schema import LlmResponseBase

router = APIRouter()

@router.post("/ask_question", response_model=LlmResponseBase)
async def ask_question_route(request: Request, body: LlmRequestBase) -> LlmResponseBase:

    start = time.perf_counter()

    config = request.app.state.config
    vector_db_service  = request.app.state.vector_db_service
    wikis_collection = request.app.state.wikis_collection

    answer = await ask_question(body.question, config, wikis_collection, vector_db_service)

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"
    
    return LlmResponseBase(answer=answer, duration=duration)
