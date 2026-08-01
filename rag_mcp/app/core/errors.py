from collections.abc import Mapping
from typing import Any, ClassVar

_SAFE_DETAIL_KEYS = frozenset(
    {
        "configuration",
        "dependency",
        "error_type",
        "operation",
        "status_code",
    }
)


class McpError(RuntimeError):
    """Base des erreurs MCP exposables sans donnée sensible."""

    code: ClassVar[str] = "mcp_error"
    default_public_message: ClassVar[str] = "L'outil RAG n'a pas pu traiter la demande."
    default_retryable: ClassVar[bool] = False

    def __init__(
        self,
        public_message: str | None = None,
        *,
        safe_details: Mapping[str, Any] | None = None,
        retryable: bool | None = None,
    ) -> None:
        """Initialise une erreur avec son contrat public et son diagnostic sûr.

        Args:
            public_message: Message destiné au client MCP, sans détail technique.
            safe_details: Métadonnées à faible cardinalité autorisées dans les logs.
            retryable: Surcharge éventuelle du caractère temporaire de l'erreur.
        """
        self.public_message = public_message or self.default_public_message
        self.safe_details = _filter_safe_details(safe_details)
        self.retryable = self.default_retryable if retryable is None else retryable
        super().__init__(self.public_message)

    def to_public_dict(self) -> dict[str, Any]:
        """Construit la partie structurée sûre retournée au client MCP.

        Returns:
            Code stable, message public, indicateur de nouvelle tentative et détails sûrs.
        """
        return {
            "code": self.code,
            "message": self.public_message,
            "retryable": self.retryable,
            "details": self.safe_details,
        }


class McpConfigError(McpError):
    """Signale une configuration obligatoire absente ou invalide."""

    code = "configuration_error"
    default_public_message = "La configuration du serveur MCP est invalide."


class McpAuthError(McpError):
    """Signale une authentification MCP absente ou refusée."""

    code = "authentication_error"
    default_public_message = "L'authentification MCP est requise."


class McpRagClientError(McpError):
    """Base des erreurs classifiées à la frontière de l'orchestrator."""

    code = "rag_client_error"
    default_public_message = "Le service RAG n'a pas pu traiter la demande."


class McpTimeoutError(McpRagClientError):
    """Signale que l'orchestrator a dépassé le délai autorisé."""

    code = "upstream_timeout"
    default_public_message = "Le service RAG met trop de temps à répondre."
    default_retryable = True


class McpConnectionError(McpRagClientError):
    """Signale une connexion impossible vers l'orchestrator."""

    code = "upstream_connection_error"
    default_public_message = "Le service RAG est temporairement injoignable."
    default_retryable = True


class McpUnauthorizedError(McpRagClientError):
    """Signale que l'orchestrator refuse le bearer token courant."""

    code = "upstream_unauthorized"
    default_public_message = "La session MCP n'est plus autorisée."


class McpForbiddenError(McpRagClientError):
    """Signale que l'utilisateur ne peut pas exécuter l'opération RAG."""

    code = "upstream_forbidden"
    default_public_message = "L'accès à la documentation RAG est refusé."


class McpRateLimitError(McpRagClientError):
    """Signale une limite temporaire appliquée par l'orchestrator."""

    code = "upstream_rate_limited"
    default_public_message = "Le service RAG est temporairement limité."
    default_retryable = True


class McpUpstreamServerError(McpRagClientError):
    """Signale une indisponibilité serveur de l'orchestrator."""

    code = "upstream_server_error"
    default_public_message = "Le service RAG est momentanément indisponible."
    default_retryable = True


class McpUpstreamHttpError(McpRagClientError):
    """Signale un autre statut HTTP d'échec de l'orchestrator."""

    code = "upstream_http_error"


class McpInvalidJsonError(McpRagClientError):
    """Signale une réponse qui n'est pas un document JSON lisible."""

    code = "upstream_invalid_json"
    default_public_message = "Le service RAG a retourné une réponse illisible."


class McpResponseContractError(McpRagClientError):
    """Signale une réponse JSON incompatible avec le contrat attendu."""

    code = "upstream_contract_error"
    default_public_message = "Le service RAG a retourné une réponse invalide."


def _filter_safe_details(
    details: Mapping[str, Any] | None,
) -> dict[str, str | int | bool]:
    """Conserve uniquement les métadonnées explicitement autorisées.

    Args:
        details: Métadonnées candidates provenant d'une frontière technique.

    Returns:
        Dictionnaire borné ne contenant ni URL, ni corps, ni token.
    """
    if not details:
        return {}

    filtered: dict[str, str | int | bool] = {}
    for key, value in details.items():
        if key not in _SAFE_DETAIL_KEYS or not isinstance(value, str | int | bool):
            continue
        filtered[key] = value[:128] if isinstance(value, str) else value
    return filtered
