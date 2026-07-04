import logging
import time

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_config, get_current_user, get_db_pool
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase
from app.services.ask_question_service import (
    ask_question_to_api,
    ask_question_to_local_model,
)
from app.services.retrieve_chunks_service import retrieve_chunks
from app.services.usage_tracking_service import (
    QUOTA_EXCEEDED_MESSAGE,
    QuotaExceededError,
    check_user_token_quota,
    finish_usage_session,
    save_failed_question_usage,
    save_retrieval_usage,
    save_successful_question_usage,
    start_usage_session,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ask_question", response_model=AskQuestionResponseBase)
async def ask_question_route(
    body: AskQuestionRequestBase,
    current_user: AuthenticatedUser = Depends(get_current_user),
    config=Depends(get_config),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):
    start = time.perf_counter()
    session_id: int | None = None
    rag_completed = False

    try:
        user_id, session_id = await start_usage_session(current_user, db_pool, body.channel)
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception

    try:
        await check_user_token_quota(db_pool, user_id)
    except QuotaExceededError as exception:
        duration_ms = _elapsed_ms(start)

        try:
            await save_failed_question_usage(
                db_pool=db_pool,
                session_id=session_id,
                question=body.question,
                status="quota_exceeded",
                duration_ms=duration_ms,
            )
        except Exception:
            logger.exception("Failed to save quota exceeded RAG interaction")

        try:
            await finish_usage_session(db_pool, session_id)
        except Exception:
            logger.exception("Failed to finish quota exceeded usage session")

        raise HTTPException(
            status_code=403,
            detail=QUOTA_EXCEEDED_MESSAGE,
        ) from exception

    try:
        if body.provider == "local":
            answer: AskQuestionResponseBase = await ask_question_to_local_model(
                body.question, config
            )
        else:
            answer = await ask_question_to_api(body.question, config, db_pool)

        rag_completed = True
        duration_ms = _elapsed_ms(start)
        answer.duration = _format_duration(duration_ms)

        await save_successful_question_usage(
            db_pool=db_pool,
            session_id=session_id,
            question=body.question,
            llm_provider=_get_llm_provider(body.provider, config),
            answer=answer,
            duration_ms=duration_ms,
        )

        return answer
    except Exception:
        duration_ms = _elapsed_ms(start)

        if not rag_completed:
            try:
                await save_failed_question_usage(
                    db_pool=db_pool,
                    session_id=session_id,
                    question=body.question,
                    status="error",
                    duration_ms=duration_ms,
                )
            except Exception:
                logger.exception("Failed to save failed RAG interaction")

        raise
    finally:
        if session_id is not None:
            try:
                await finish_usage_session(db_pool, session_id)
            except Exception:
                logger.exception("Failed to finish usage session")


@router.post("/retrieve_chunks", response_model=RetrieveChunksResponseBase)
async def retrieve_chunks_route(
    body: RetrieveChunksRequestBase,
    current_user: AuthenticatedUser = Depends(get_current_user),
    config=Depends(get_config),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):
    start = time.perf_counter()
    session_id: int | None = None
    retrieval_completed = False

    try:
        _, session_id = await start_usage_session(current_user, db_pool, "mcp")
    except ValueError as exception:
        raise HTTPException(status_code=400, detail=str(exception)) from exception

    try:
        answer: RetrieveChunksResponseBase = await retrieve_chunks(body.question, config)

        retrieval_completed = True
        duration_ms = _elapsed_ms(start)

        await save_retrieval_usage(
            db_pool=db_pool,
            session_id=session_id,
            question=body.question,
            retrieved_chunks=answer.retrieved_chunks,
            duration_ms=duration_ms,
        )

        return answer
    except Exception:
        duration_ms = _elapsed_ms(start)

        if not retrieval_completed:
            try:
                await save_failed_question_usage(
                    db_pool=db_pool,
                    session_id=session_id,
                    question=body.question,
                    status="error",
                    duration_ms=duration_ms,
                )
            except Exception:
                logger.exception("Failed to save failed MCP retrieval interaction")

        raise
    finally:
        if session_id is not None:
            try:
                await finish_usage_session(db_pool, session_id)
            except Exception:
                logger.exception("Failed to finish MCP usage session")


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _format_duration(duration_ms: int) -> str:
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes:02d}:{seconds:02d}"


def _get_llm_provider(provider: str, config: dict) -> str:
    return config["llm"][provider]["provider"]
