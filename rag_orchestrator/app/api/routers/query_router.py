import time

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_config
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase
from app.services.ask_question_service import (
    ask_question_to_api,
    ask_question_to_local_model,
)
from app.services.retrieve_chunks_service import retrieve_chunks

router = APIRouter()


@router.post("/ask_question", response_model=AskQuestionResponseBase)
async def ask_question_route(
    body: AskQuestionRequestBase,
    config=Depends(get_config),
):
    start = time.perf_counter()

    if body.provider == "local":
        answer: AskQuestionResponseBase = await ask_question_to_local_model(
            body.question, config
        )
    elif body.provider == "api":
        answer: AskQuestionResponseBase = await ask_question_to_api(
            body.question, config
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"

    answer.duration = duration

    return answer


@router.post("/retrieve_chunks", response_model=RetrieveChunksResponseBase)
async def retrieve_chunks_route(
    body: RetrieveChunksRequestBase,
    config=Depends(get_config),
):
    answer: RetrieveChunksResponseBase = await retrieve_chunks(body.question, config)

    return answer
