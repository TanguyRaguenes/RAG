import logging
import time
from typing import Any, Protocol

import asyncpg
from opentelemetry import trace

from app.core.exceptions import (
    QuestionQuotaExceededError,
    QuotaExceededError,
    QuotaInactiveError,
    UsageSessionValidationError,
)
from app.core.orchestration_observability import (
    elapsed_ms,
    format_duration,
    get_llm_provider,
    record_orchestration_error,
    record_orchestration_success,
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
    check_user_token_quota,
    finish_usage_session,
    save_failed_question_usage,
    save_retrieval_usage,
    save_successful_question_usage,
    start_usage_session,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class QuestionOrchestrationServiceProtocol(Protocol):
    """Contrat injecté dans les routes HTTP du pipeline de question."""

    async def ask_question(
        self,
        body: AskQuestionRequestBase,
        current_user: AuthenticatedUser,
    ) -> AskQuestionResponseBase:
        """Exécute le pipeline RAG complet pour une question utilisateur.

        Args:
            body: Question et options validées par le schéma HTTP.
            current_user: Identité validée par la dépendance OIDC.

        Returns:
            Réponse RAG enrichie des informations publiques d'usage.
        """
        ...

    async def retrieve_chunks(
        self,
        body: RetrieveChunksRequestBase,
        current_user: AuthenticatedUser,
    ) -> RetrieveChunksResponseBase:
        """Exécute le pipeline de récupération destiné au serveur MCP.

        Args:
            body: Question documentaire validée par le schéma HTTP.
            current_user: Identité validée par la dépendance OIDC.

        Returns:
            Chunks pertinents retournés au client MCP.
        """
        ...


class QuestionOrchestrationService:
    """Orchestre le pipeline RAG et son suivi d'usage hors de la couche HTTP."""

    def __init__(self, config: dict[str, Any], db_pool: asyncpg.Pool) -> None:
        """Conserve les ressources nécessaires aux deux opérations RAG.

        Args:
            config: Configuration applicative chargée au démarrage.
            db_pool: Pool PostgreSQL utilisé pour les quotas et le suivi d'usage.
        """
        self.config = config
        self.db_pool = db_pool

    async def ask_question(
        self,
        body: AskQuestionRequestBase,
        current_user: AuthenticatedUser,
    ) -> AskQuestionResponseBase:
        """Traite une question et persiste son résultat dans une session toujours clôturée.

        Args:
            body: Question, fournisseur LLM et canal demandés par le client.
            current_user: Utilisateur authentifié issu de la dépendance OIDC.

        Returns:
            Réponse RAG enrichie de la durée et de l'identifiant d'interaction.

        Raises:
            UsageSessionValidationError: Si la session d'usage ne peut pas démarrer.
            QuestionQuotaExceededError: Si le quota mensuel est atteint.
            Exception: Si le pipeline RAG ou sa persistance principale échoue.
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
                    self.db_pool,
                    body.channel,
                )
            except ValueError as exception:
                record_orchestration_error(operation, "validation_error", start)
                raise UsageSessionValidationError(
                    "Usage session creation validation failed"
                ) from exception

            try:
                try:
                    await check_user_token_quota(self.db_pool, user_id)
                except (QuotaExceededError, QuotaInactiveError) as exception:
                    await self._save_failed_usage_safely(
                        session_id=session_id,
                        question=body.question,
                        status="quota_exceeded",
                        duration_ms=elapsed_ms(start),
                        log_message="Failed to save quota exceeded RAG interaction",
                    )
                    record_orchestration_error(operation, "quota_exceeded", start)
                    raise QuestionQuotaExceededError(
                        "Question rejected by user quota"
                    ) from exception

                if body.provider == "local":
                    answer = await ask_question_to_local_model(
                        body.question,
                        self.config,
                    )
                else:
                    answer = await ask_question_to_api(
                        body.question,
                        self.config,
                    )

                rag_completed = True
                duration_ms = elapsed_ms(start)
                answer.duration = format_duration(duration_ms)
                answer.interaction_id = await save_successful_question_usage(
                    db_pool=self.db_pool,
                    session_id=session_id,
                    question=body.question,
                    llm_provider=get_llm_provider(body.provider, self.config),
                    answer=answer,
                    duration_ms=duration_ms,
                )
                record_orchestration_success(
                    operation,
                    start,
                    len(answer.retrieved_chunks),
                )
                return answer
            except QuestionQuotaExceededError:
                raise
            except Exception as exception:
                if not rag_completed:
                    await self._save_failed_usage_safely(
                        session_id=session_id,
                        question=body.question,
                        status="error",
                        duration_ms=elapsed_ms(start),
                        log_message="Failed to save failed RAG interaction",
                    )
                record_orchestration_error(operation, type(exception).__name__, start)
                raise
            finally:
                await self._finish_usage_session_safely(
                    session_id,
                    "Failed to finish usage session",
                )

    async def retrieve_chunks(
        self,
        body: RetrieveChunksRequestBase,
        current_user: AuthenticatedUser,
    ) -> RetrieveChunksResponseBase:
        """Récupère les chunks MCP et clôture systématiquement la session démarrée.

        Args:
            body: Question documentaire envoyée par le serveur MCP.
            current_user: Utilisateur authentifié issu de la dépendance OIDC.

        Returns:
            Chunks récupérés et rerankés pour la question.

        Raises:
            UsageSessionValidationError: Si la session d'usage ne peut pas démarrer.
            Exception: Si le pipeline de retrieval ou sa persistance échoue.
        """
        start = time.perf_counter()
        session_id: int | None = None
        retrieval_completed = False
        operation = "retrieve_chunks"

        with tracer.start_as_current_span("orchestrator.retrieve_chunks"):
            try:
                _, session_id = await start_usage_session(
                    current_user,
                    self.db_pool,
                    "mcp",
                )
            except ValueError as exception:
                record_orchestration_error(operation, "validation_error", start)
                raise UsageSessionValidationError(
                    "Usage session creation validation failed"
                ) from exception

            try:
                answer = await retrieve_chunks(body.question, self.config)
                retrieval_completed = True
                duration_ms = elapsed_ms(start)
                await save_retrieval_usage(
                    db_pool=self.db_pool,
                    session_id=session_id,
                    question=body.question,
                    retrieved_chunks=answer.retrieved_chunks,
                    duration_ms=duration_ms,
                )
                record_orchestration_success(
                    operation,
                    start,
                    len(answer.retrieved_chunks),
                )
                return answer
            except Exception as exception:
                if not retrieval_completed:
                    await self._save_failed_usage_safely(
                        session_id=session_id,
                        question=body.question,
                        status="error",
                        duration_ms=elapsed_ms(start),
                        log_message="Failed to save failed MCP retrieval interaction",
                    )
                record_orchestration_error(operation, type(exception).__name__, start)
                raise
            finally:
                await self._finish_usage_session_safely(
                    session_id,
                    "Failed to finish MCP usage session",
                )

    async def _save_failed_usage_safely(
        self,
        *,
        session_id: int | None,
        question: str,
        status: str,
        duration_ms: int,
        log_message: str,
    ) -> None:
        """Persiste un échec sans masquer l'erreur principale du pipeline.

        Args:
            session_id: Session créée avant l'échec, ou `None` si absente.
            question: Question associée à l'interaction échouée.
            status: Statut fonctionnel enregistré en base.
            duration_ms: Durée écoulée avant l'échec.
            log_message: Message interne émis si la persistance secondaire échoue.
        """
        if session_id is None:
            return

        try:
            await save_failed_question_usage(
                db_pool=self.db_pool,
                session_id=session_id,
                question=question,
                status=status,
                duration_ms=duration_ms,
            )
        except Exception as exception:  # noqa: BLE001 - secondary persistence must not mask the primary error
            logger.error(
                log_message,
                extra={"error_type": type(exception).__name__},
            )

    async def _finish_usage_session_safely(
        self,
        session_id: int | None,
        log_message: str,
    ) -> None:
        """Clôture une session sans masquer le résultat principal de la requête.

        Args:
            session_id: Identifiant de la session à clôturer, ou `None` si absente.
            log_message: Message interne émis si la clôture échoue.
        """
        if session_id is None:
            return

        try:
            await finish_usage_session(self.db_pool, session_id)
        except Exception as exception:  # noqa: BLE001 - cleanup must not mask the request result
            logger.error(
                log_message,
                extra={"error_type": type(exception).__name__},
            )
