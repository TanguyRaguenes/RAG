from collections.abc import Callable
from typing import Protocol, Self

import httpx

from app.core.config import McpConfig
from app.core.errors import (
    McpConnectionError,
    McpForbiddenError,
    McpInvalidJsonError,
    McpRateLimitError,
    McpTimeoutError,
    McpUnauthorizedError,
    McpUpstreamHttpError,
    McpUpstreamServerError,
)
from app.schemas.rag_response import RetrievedChunksResponse


class AsyncHttpClientProtocol(Protocol):
    """Contrat HTTP minimal utilisé par le client RAG."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, *args: object) -> bool | None: ...

    async def post(
        self,
        url: str,
        *,
        json: dict[str, str],
        headers: dict[str, str],
    ) -> httpx.Response: ...


HttpClientFactory = Callable[..., AsyncHttpClientProtocol]


class RagClient:
    """Client HTTP de l'orchestrator dédié à la récupération de chunks."""

    def __init__(
        self,
        config: McpConfig,
        client_factory: HttpClientFactory = httpx.AsyncClient,
    ) -> None:
        """Prépare le client avec une factory HTTP remplaçable en test.

        Args:
            config: Configuration contenant l'endpoint de récupération.
            client_factory: Factory créant le client HTTP asynchrone.
        """
        self._config = config
        self._client_factory = client_factory

    async def retrieve_documentation_chunks(
        self,
        question: str,
        access_token: str,
    ) -> RetrievedChunksResponse:
        """Récupère et valide les chunks auprès de l'orchestrator.

        Args:
            question: Question reçue via l'outil MCP, non loggée.
            access_token: Token OIDC transmis dans l'en-tête Authorization.

        Returns:
            DTO contenant les chunks retournés par l'orchestrator.

        Raises:
            McpRagClientError: Si l'appel échoue ou retourne une réponse invalide.
        """
        try:
            async with self._client_factory(timeout=120) as client:
                response = await client.post(
                    self._config.rag_orchestrator_url,
                    json={"question": question},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.TimeoutException as exception:
            raise McpTimeoutError(
                safe_details={
                    "dependency": "rag_orchestrator",
                    "operation": "retrieve_documentation_chunks",
                }
            ) from exception
        except httpx.ConnectError as exception:
            raise McpConnectionError(
                safe_details={
                    "dependency": "rag_orchestrator",
                    "operation": "retrieve_documentation_chunks",
                }
            ) from exception
        except httpx.RequestError as exception:
            raise McpConnectionError(
                safe_details={
                    "dependency": "rag_orchestrator",
                    "error_type": type(exception).__name__,
                    "operation": "retrieve_documentation_chunks",
                }
            ) from exception

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exception:
            raise _http_status_error(exception.response.status_code) from exception

        try:
            payload = response.json()
        except ValueError as exception:
            raise McpInvalidJsonError(
                safe_details={"dependency": "rag_orchestrator"}
            ) from exception

        return RetrievedChunksResponse.from_payload(payload)


def _http_status_error(status_code: int) -> McpUpstreamHttpError:
    """Classe un statut HTTP sans lire le corps de la réponse.

    Args:
        status_code: Statut numérique retourné par l'orchestrator.

    Returns:
        Erreur applicative correspondant au statut reçu.
    """
    details = {"dependency": "rag_orchestrator", "status_code": status_code}
    if status_code == 401:
        return McpUnauthorizedError(safe_details=details)
    if status_code == 403:
        return McpForbiddenError(safe_details=details)
    if status_code == 429:
        return McpRateLimitError(safe_details=details)
    if status_code >= 500:
        return McpUpstreamServerError(safe_details=details)
    return McpUpstreamHttpError(safe_details=details)
