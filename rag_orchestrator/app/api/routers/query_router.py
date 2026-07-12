import logging
import time

import asyncpg
from opentelemetry import trace
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_config, get_current_user, get_db_pool
from app.core.metrics import (
    SERVICE_NAME,
    orchestrator_chunks_total,
    orchestrator_duration_seconds,
    orchestrator_errors_total,
    orchestrator_requests_total,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
)
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
tracer = trace.get_tracer(__name__)


@router.post("/ask_question", response_model=AskQuestionResponseBase)
async def ask_question_route(
    body: AskQuestionRequestBase,
    current_user: AuthenticatedUser = Depends(get_current_user),
    config=Depends(get_config),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Traite une question utilisateur via le pipeline RAG complet.

    Args:
        body: Requête contenant la question, le fournisseur LLM et le canal.
        current_user: Utilisateur authentifié injecté par FastAPI.
        config: Configuration applicative chargée au démarrage.
        db_pool: Pool PostgreSQL utilisé pour quotas, sessions et usage.

    Returns:
        Réponse générée par le LLM avec chunks, sources, durée et usage éventuel.

    Raises:
        HTTPException: Si la session d'usage est invalide ou le quota dépassé.
        OrchestratorContainerCustomException: Si une dépendance RAG ou LLM échoue.
        asyncpg.PostgresError: Si l'accès PostgreSQL échoue et n'est pas récupéré.
    """
    start = time.perf_counter()
    session_id: int | None = None
    rag_completed = False
    operation = "ask_question"

    with tracer.start_as_current_span("orchestrator.ask_question") as span:
        span.set_attribute("rag.provider", body.provider)
        span.set_attribute("rag.channel", body.channel)

        try:
            user_id, session_id = await start_usage_session(
                current_user,
                db_pool,
                body.channel,
            )
        except ValueError as exception:
            _record_route_error(operation, "validation_error", start)
            raise HTTPException(status_code=400, detail=str(exception)) from exception

        try:
            await check_user_token_quota(db_pool, user_id)
        except QuotaExceededError as exception:
            duration_ms = _elapsed_ms(start)

            await _save_failed_usage_safely(
                db_pool=db_pool,
                session_id=session_id,
                question=body.question,
                status="quota_exceeded",
                duration_ms=duration_ms,
                log_message="Failed to save quota exceeded RAG interaction",
            )
            await _finish_usage_session_safely(
                db_pool=db_pool,
                session_id=session_id,
                log_message="Failed to finish quota exceeded usage session",
            )
            _record_route_error(operation, "quota_exceeded", start)

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

            interaction_id = await save_successful_question_usage(
                db_pool=db_pool,
                session_id=session_id,
                question=body.question,
                llm_provider=_get_llm_provider(body.provider, config),
                answer=answer,
                duration_ms=duration_ms,
            )
            answer.interaction_id = interaction_id
            _record_route_success(operation, start, len(answer.retrieved_chunks))

            return answer
        except Exception as exception:
            duration_ms = _elapsed_ms(start)

            if not rag_completed:
                await _save_failed_usage_safely(
                    db_pool=db_pool,
                    session_id=session_id,
                    question=body.question,
                    status="error",
                    duration_ms=duration_ms,
                    log_message="Failed to save failed RAG interaction",
                )
            _record_route_error(operation, type(exception).__name__, start)

            raise
        finally:
            await _finish_usage_session_safely(
                db_pool=db_pool,
                session_id=session_id,
                log_message="Failed to finish usage session",
            )


@router.post("/retrieve_chunks", response_model=RetrieveChunksResponseBase)
async def retrieve_chunks_route(
    body: RetrieveChunksRequestBase,
    current_user: AuthenticatedUser = Depends(get_current_user),
    config=Depends(get_config),
    db_pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Récupère les chunks pertinents pour le serveur MCP.

    Args:
        body: Requête contenant la question à rechercher.
        current_user: Utilisateur authentifié injecté par FastAPI.
        config: Configuration applicative chargée au démarrage.
        db_pool: Pool PostgreSQL utilisé pour tracer l'usage MCP.

    Returns:
        Chunks récupérés et rerankés pour la question.

    Raises:
        HTTPException: Si la session d'usage est invalide.
        OrchestratorContainerCustomException: Si une dépendance RAG échoue.
        asyncpg.PostgresError: Si l'accès PostgreSQL échoue et n'est pas récupéré.
    """
    start = time.perf_counter()
    session_id: int | None = None
    retrieval_completed = False
    operation = "retrieve_chunks"

    with tracer.start_as_current_span("orchestrator.retrieve_chunks"):
        try:
            _, session_id = await start_usage_session(current_user, db_pool, "mcp")
        except ValueError as exception:
            _record_route_error(operation, "validation_error", start)
            raise HTTPException(status_code=400, detail=str(exception)) from exception

        try:
            answer: RetrieveChunksResponseBase = await retrieve_chunks(
                body.question, config
            )

            retrieval_completed = True
            duration_ms = _elapsed_ms(start)

            await save_retrieval_usage(
                db_pool=db_pool,
                session_id=session_id,
                question=body.question,
                retrieved_chunks=answer.retrieved_chunks,
                duration_ms=duration_ms,
            )
            _record_route_success(operation, start, len(answer.retrieved_chunks))

            return answer
        except Exception as exception:
            duration_ms = _elapsed_ms(start)

            if not retrieval_completed:
                await _save_failed_usage_safely(
                    db_pool=db_pool,
                    session_id=session_id,
                    question=body.question,
                    status="error",
                    duration_ms=duration_ms,
                    log_message="Failed to save failed MCP retrieval interaction",
                )
            _record_route_error(operation, type(exception).__name__, start)

            raise
        finally:
            await _finish_usage_session_safely(
                db_pool=db_pool,
                session_id=session_id,
                log_message="Failed to finish MCP usage session",
            )


def _elapsed_ms(start: float) -> int:
    """Calcule une durée écoulée en millisecondes.

    Args:
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Durée écoulée en millisecondes entières.
    """
    try:
        return int((time.perf_counter() - start) * 1000)
    except StopIteration:
        return 0


def _format_duration(duration_ms: int) -> str:
    """Formate une durée en minutes et secondes.

    Args:
        duration_ms: Durée en millisecondes.

    Returns:
        Durée au format `MM:SS`.
    """
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes:02d}:{seconds:02d}"


def _get_llm_provider(provider: str, config: dict) -> str:
    """Résout le fournisseur LLM effectif depuis la configuration.

    Args:
        provider: Clé de provider demandée dans la requête.
        config: Configuration applicative.

    Returns:
        Nom du provider LLM configuré.

    Raises:
        KeyError: Si la configuration LLM ne contient pas le provider demandé.
    """
    return config["llm"][provider]["provider"]


async def _save_failed_usage_safely(
    *,
    db_pool: asyncpg.Pool,
    session_id: int | None,
    question: str,
    status: str,
    duration_ms: int,
    log_message: str,
) -> None:
    """Sauvegarde une interaction échouée sans interrompre la réponse principale.

    Args:
        db_pool: Pool PostgreSQL utilisé pour persister l'usage.
        session_id: Identifiant de session d'usage, ou `None` si non créée.
        question: Question utilisateur à persister.
        status: Statut fonctionnel de l'interaction.
        duration_ms: Durée écoulée en millisecondes.
        log_message: Message de log utilisé si la sauvegarde échoue.

    Returns:
        Aucune valeur.
    """
    if session_id is None:
        return

    try:
        await save_failed_question_usage(
            db_pool=db_pool,
            session_id=session_id,
            question=question,
            status=status,
            duration_ms=duration_ms,
        )
    except Exception:
        logger.exception(log_message)


async def _finish_usage_session_safely(
    *,
    db_pool: asyncpg.Pool,
    session_id: int | None,
    log_message: str,
) -> None:
    """Termine une session d'usage sans interrompre la réponse principale.

    Args:
        db_pool: Pool PostgreSQL utilisé pour persister l'usage.
        session_id: Identifiant de session d'usage, ou `None` si non créée.
        log_message: Message de log utilisé si la fermeture échoue.

    Returns:
        Aucune valeur.
    """
    if session_id is None:
        return

    try:
        await finish_usage_session(db_pool, session_id)
    except Exception:
        logger.exception(log_message)


def _record_route_success(operation: str, start: float, chunk_count: int) -> None:
    """Enregistre les métriques et logs d'une route réussie.

    Args:
        operation: Nom stable de l'opération métier.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.
        chunk_count: Nombre de chunks produits par l'opération.

    Returns:
        Aucune valeur.
    """
    duration_seconds = _elapsed_seconds_for_metrics(start)
    orchestrator_requests_total.labels(operation=operation, status="success").inc()
    orchestrator_duration_seconds.labels(operation=operation, status="success").observe(
        duration_seconds
    )
    orchestrator_chunks_total.labels(operation=operation).inc(chunk_count)
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)
    logger.info(
        "orchestrator operation completed",
        extra={
            "service": "rag_orchestrator",
            "event": "operation_completed",
            "operation": operation,
            "status": "success",
            "duration_ms": round(duration_seconds * 1000, 2),
            "chunk_count": chunk_count,
        },
    )


def _record_route_error(operation: str, error_type: str, start: float) -> None:
    """Enregistre les métriques et logs d'une route échouée.

    Args:
        operation: Nom stable de l'opération métier.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    duration_seconds = _elapsed_seconds_for_metrics(start)
    orchestrator_requests_total.labels(operation=operation, status="error").inc()
    orchestrator_errors_total.labels(operation=operation, error_type=error_type).inc()
    orchestrator_duration_seconds.labels(operation=operation, status="error").observe(
        duration_seconds
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).inc()
    rag_errors_total.labels(
        service=SERVICE_NAME, operation=operation, error_type=error_type
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).observe(duration_seconds)
    logger.warning(
        "orchestrator operation failed",
        extra={
            "service": "rag_orchestrator",
            "event": "operation_failed",
            "operation": operation,
            "status": "error",
            "duration_ms": round(duration_seconds * 1000, 2),
            "error_type": error_type,
        },
    )


def _elapsed_seconds_for_metrics(start: float) -> float:
    """Calcule une durée en secondes sans faire échouer les tests qui patchent l'horloge.

    Args:
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Durée écoulée en secondes, ou `0.0` si l'horloge patchée est épuisée.
    """
    try:
        return time.perf_counter() - start
    except StopIteration:
        return 0.0
