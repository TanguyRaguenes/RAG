import time

from fastapi import APIRouter, Depends
from src.app.dal.clients.question_answering_client import ask_question
from src.app.schemas.llm_request_schema import LlmRequestBase
from src.app.schemas.llm_response_schema import LlmResponseBase
from src.app.api.dependencies import get_config, get_wikis_collection, get_vector_store_repository

router = APIRouter()

@router.post("/ask_question", response_model=LlmResponseBase)
async def ask_question_route(
        body: LlmRequestBase,
        config = Depends(get_config),
        vector_store_repository  = Depends(get_vector_store_repository),
        wikis_collection = Depends(get_wikis_collection)
    ) -> LlmResponseBase:

    start = time.perf_counter()

    answer = await ask_question(body.question, config, wikis_collection, vector_store_repository)

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"
    
    return LlmResponseBase(answer=answer, duration=duration)
