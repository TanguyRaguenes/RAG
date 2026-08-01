import os
import time
from typing import Literal, NoReturn, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from opentelemetry import trace
from pydantic import ValidationError

from app.core.config import RagProvider
from app.core.exceptions import (
    EvaluatorAuthenticationError,
    EvaluatorAuthorizationError,
    EvaluatorClientError,
)
from app.core.metrics import (
    evaluator_errors_total,
    evaluator_external_call_duration_seconds,
)
from app.schemas.orchestrator_schema import (
    AskQuestionRequest,
    AskQuestionResponse,
    AuthenticatedUser,
)

tracer = trace.get_tracer(__name__)


class RagOrchestratorClient(Protocol):
    """Contrat d'authentification et de questionnement de l'orchestrator."""

    async def get_current_user(self, access_token: str) -> AuthenticatedUser:
        """Résout l'identité associée au bearer courant.

        Args:
            access_token: Bearer opaque reçu par l'evaluator.

        Returns:
            Identité et groupes validés par l'orchestrator.

        Raises:
            EvaluatorContainerCustomException: Si l'identité ne peut pas être vérifiée.
        """
        ...

    async def ask_question(
        self, question: str, access_token: str
    ) -> AskQuestionResponse:
        """Pose une question avec le bearer déjà autorisé.

        Args:
            question: Question issue d'un cas validé du dataset.
            access_token: Bearer à propager à l'orchestrator.

        Returns:
            Réponse de l'orchestrator conforme au schéma attendu.

        Raises:
            EvaluatorContainerCustomException: Si l'appel ou le contrat de réponse échoue.
        """
        ...


class HttpRagOrchestratorClient:
    """Client HTTP authentifié de `rag_orchestrator`."""

    def __init__(
        self,
        ask_question_url: str,
        auth_me_url: str | None = None,
        timeout_seconds: float = 180.0,
        rag_provider: RagProvider = "api",
    ) -> None:
        """Configure les endpoints authentifiés de l'orchestrator.

        Args:
            ask_question_url: URL complète de l'endpoint `ask_question`.
            auth_me_url: URL `/auth/me`, dérivée de l'URL précédente si absente.
            timeout_seconds: Délai maximal des appels à l'orchestrator.
            rag_provider: Fournisseur RAG obligatoire envoyé avec chaque question.

        Raises:
            EvaluatorClientError: Si une URL n'est pas une URL HTTP exploitable.
        """
        self._ask_question_url = _validate_http_url(ask_question_url)
        self._auth_me_url = _validate_http_url(
            auth_me_url or derive_auth_me_url(ask_question_url)
        )
        self._timeout_seconds = timeout_seconds
        self._rag_provider = rag_provider

    @classmethod
    def from_environment(
        cls, rag_provider: RagProvider = "api"
    ) -> "HttpRagOrchestratorClient":
        """Construit le client depuis les variables du conteneur.

        Returns:
            Client configuré avec une URL d'auth explicite ou dérivée.

        Args:
            rag_provider: Fournisseur RAG issu de la configuration typée evaluator.

        Raises:
            EvaluatorClientError: Si l'URL de questionnement obligatoire est absente.
        """
        ask_question_url = os.getenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL")
        if not ask_question_url:
            raise EvaluatorClientError(
                message="URL de l'orchestrator non configurée",
                details={"env_var": "RAG_ORCHESTRATOR_ASK_QUESTION_URL"},
            )
        return cls(
            ask_question_url=ask_question_url,
            auth_me_url=os.getenv("RAG_ORCHESTRATOR_AUTH_ME_URL"),
            rag_provider=rag_provider,
        )

    async def get_current_user(self, access_token: str) -> AuthenticatedUser:
        """Vérifie le bearer auprès de `/auth/me`.

        Args:
            access_token: Bearer opaque transmis sans journalisation.

        Returns:
            Identité authentifiée et groupes associés.

        Raises:
            EvaluatorContainerCustomException: Si le bearer ou la réponse est invalide.
        """
        data, start = await self._request_json(
            method="GET",
            url=self._auth_me_url,
            operation="auth_me",
            access_token=access_token,
        )
        try:
            user = AuthenticatedUser.model_validate(data)
        except ValidationError as exception:
            _record_external_error("auth_me", "invalid_format", start)
            raise EvaluatorClientError(
                message="L'orchestrator a retourné une identité invalide",
                details={"validation_errors": exception.error_count()},
            ) from exception
        _record_external_success("auth_me", start)
        return user

    async def ask_question(
        self, question: str, access_token: str
    ) -> AskQuestionResponse:
        """Appelle l'orchestrator avec le bearer de la requête evaluator.

        Args:
            question: Question du dataset, non journalisée.
            access_token: Bearer opaque à propager dans `Authorization`.

        Returns:
            Réponse externe validée intégralement.

        Raises:
            EvaluatorContainerCustomException: Si le transport ou la réponse échoue.
        """
        data, start = await self._request_json(
            method="POST",
            url=self._ask_question_url,
            operation="ask_question",
            access_token=access_token,
            payload=AskQuestionRequest(
                question=question,
                provider=self._rag_provider,
                channel="api",
            ).model_dump(),
        )
        try:
            result = AskQuestionResponse.model_validate(data)
        except ValidationError as exception:
            _record_external_error("ask_question", "invalid_format", start)
            raise EvaluatorClientError(
                message="L'orchestrator a retourné une réponse invalide",
                details={"validation_errors": exception.error_count()},
            ) from exception
        _record_external_success("ask_question", start)
        return result

    async def _request_json(
        self,
        *,
        method: Literal["GET", "POST"],
        url: str,
        operation: str,
        access_token: str,
        payload: dict[str, object] | None = None,
    ) -> tuple[object, float]:
        """Exécute un appel authentifié sans exposer le bearer.

        Args:
            method: Méthode HTTP autorisée pour les endpoints orchestrator.
            url: Endpoint validé à appeler.
            operation: Nom stable utilisé par les métriques.
            access_token: Bearer opaque placé uniquement dans le header HTTP.
            payload: Corps JSON optionnel de la requête.

        Returns:
            JSON brut et instant initial utilisés pour valider puis mesurer la réponse.

        Raises:
            EvaluatorContainerCustomException: Si le transport, le statut ou le JSON échoue.
        """
        start = time.perf_counter()
        request_kwargs: dict[str, object] = {
            "headers": _build_bearer_headers(access_token)
        }
        if payload is not None:
            request_kwargs["json"] = payload

        try:
            with tracer.start_as_current_span(f"evaluator.orchestrator.{operation}"):
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.request(method, url, **request_kwargs)
                    response.raise_for_status()
                    data: object = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error(operation, "http_status", start)
            _raise_status_error(
                exception.response.status_code,
                operation,
                exception,
            )
        except httpx.ConnectError as exception:
            _record_external_error(operation, "connect_error", start)
            raise EvaluatorClientError(
                message="Impossible de se connecter à l'orchestrator"
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error(operation, "timeout", start)
            raise EvaluatorClientError(
                message="Timeout lors de l'appel à l'orchestrator"
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error(operation, "request_error", start)
            raise EvaluatorClientError(
                message="Erreur réseau lors de l'appel à l'orchestrator"
            ) from exception
        except ValueError as exception:
            _record_external_error(operation, "invalid_json", start)
            raise EvaluatorClientError(
                message="L'orchestrator a retourné une réponse JSON invalide"
            ) from exception

        return data, start


def derive_auth_me_url(ask_question_url: str) -> str:
    """Dérive `/auth/me` en conservant un éventuel préfixe de déploiement.

    Args:
        ask_question_url: URL complète telle que `/api/ask_question?x=y`.

    Returns:
        URL sans query ni fragment, par exemple `/api/auth/me`.

    Raises:
        EvaluatorClientError: Si l'URL source n'est pas une URL HTTP absolue.
    """
    parsed = urlsplit(_validate_http_url(ask_question_url))
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        path_parts.pop()
    auth_path = "/" + "/".join([*path_parts, "auth", "me"])
    return urlunsplit((parsed.scheme, parsed.netloc, auth_path, "", ""))


def _validate_http_url(url: str) -> str:
    """Valide une URL HTTP absolue utilisée par le client orchestrator.

    Args:
        url: URL provenant de l'environnement ou de la dérivation interne.

    Returns:
        URL inchangée après validation structurelle.

    Raises:
        EvaluatorClientError: Si le schéma ou l'hôte est absent.
    """
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise EvaluatorClientError(message="URL de l'orchestrator invalide")
    return url


def _build_bearer_headers(access_token: str) -> dict[str, str]:
    """Construit le header bearer sans journaliser sa valeur.

    Args:
        access_token: Token opaque reçu par l'API evaluator.

    Returns:
        Header `Authorization` destiné uniquement à l'orchestrator.
    """
    return {"Authorization": f"Bearer {access_token}"}


def _raise_status_error(
    status_code: int,
    operation: str,
    exception: httpx.HTTPStatusError,
) -> NoReturn:
    """Transforme un statut orchestrator en erreur evaluator sûre.

    Args:
        status_code: Statut HTTP retourné par l'orchestrator.
        operation: Opération externe qui a échoué.
        exception: Erreur HTTP originale conservée comme cause sans être exposée.

    Raises:
        EvaluatorAuthenticationError: Si le bearer est refusé.
        EvaluatorAuthorizationError: Si l'orchestrator refuse l'accès.
        EvaluatorClientError: Pour tout autre statut externe.
    """
    if status_code == 401:
        raise EvaluatorAuthenticationError(
            message="Bearer invalide ou expiré"
        ) from exception
    if status_code == 403:
        raise EvaluatorAuthorizationError(
            message="Accès refusé par l'orchestrator",
            internal_message="L'orchestrator a refusé le bearer authentifié",
            internal_details={"operation": operation, "upstream_status": 403},
        ) from exception
    raise EvaluatorClientError(
        message="L'orchestrator a refusé la requête",
        internal_message="Statut HTTP inattendu retourné par l'orchestrator",
        internal_details={
            "operation": operation,
            "upstream_status": status_code,
        },
    ) from exception


def _record_external_error(operation: str, error_type: str, start: float) -> None:
    """Enregistre une erreur d'appel orchestrator.

    Args:
        operation: Nom stable de l'appel externe.
        error_type: Type technique stable de l'erreur.
        start: Instant initial utilisé pour calculer la durée.
    """
    evaluator_errors_total.labels(operation=operation, error_type=error_type).inc()
    evaluator_external_call_duration_seconds.labels(
        dependency="orchestrator", operation=operation, status="error"
    ).observe(time.perf_counter() - start)


def _record_external_success(operation: str, start: float) -> None:
    """Enregistre un appel orchestrator dont le DTO a été validé.

    Args:
        operation: Nom stable de l'appel externe.
        start: Instant initial utilisé pour calculer la durée complète.
    """
    evaluator_external_call_duration_seconds.labels(
        dependency="orchestrator", operation=operation, status="success"
    ).observe(time.perf_counter() - start)
