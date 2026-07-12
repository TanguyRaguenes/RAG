import os
from dataclasses import dataclass


@dataclass(frozen=True)
class McpConfig:
    """Configuration nécessaire au serveur MCP."""

    rag_orchestrator_url: str
    oidc_token_url: str
    oidc_client_id: str
    oidc_client_secret: str


class McpError(RuntimeError):
    """Base exception pour les erreurs du serveur MCP."""

    def __init__(self, message: str, details: dict[str, str] | None = None):
        """Initialise une exception MCP.

        Args:
            message: Message lisible décrivant l'erreur.
            details: Métadonnées non sensibles utiles au diagnostic.

        Returns:
            Aucune valeur.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class McpConfigError(McpError):
    """Configuration obligatoire manquante pour le serveur MCP."""


class McpAuthError(McpError):
    """Erreur lors de l'authentification machine-to-machine."""


class McpRagClientError(McpError):
    """Erreur lors de l'appel au RAG depuis le serveur MCP."""


def load_mcp_config() -> McpConfig:
    """Charge la configuration MCP depuis les variables d'environnement.

    Returns:
        Configuration validée du serveur MCP.

    Raises:
        McpConfigError: Si une variable obligatoire est absente.
    """
    return McpConfig(
        rag_orchestrator_url=_required_env("RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL"),
        oidc_token_url=_required_env("RAG_MCP_OIDC_TOKEN_URL"),
        oidc_client_id=_required_env("RAG_MCP_OIDC_CLIENT_ID"),
        oidc_client_secret=_required_env("RAG_MCP_OIDC_CLIENT_SECRET"),
    )


def _required_env(name: str) -> str:
    """Lit une variable d'environnement obligatoire.

    Args:
        name: Nom de la variable à lire.

    Returns:
        Valeur de la variable.

    Raises:
        McpConfigError: Si la variable est absente ou vide.
    """
    value = os.getenv(name)
    if not value:
        raise McpConfigError(f"Variable d'environnement manquante : {name}")
    return value
