import os
from dataclasses import dataclass


@dataclass(frozen=True)
class McpConfig:
    """Configuration nécessaire au serveur MCP."""

    rag_orchestrator_url: str
    oidc_issuer: str
    oidc_jwks_uri: str
    oidc_allowed_audiences: list[str]
    required_scopes: list[str]
    resource_server_url: str


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
    """Erreur lors de l'authentification entrante du client MCP."""


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
        oidc_issuer=_required_env("RAG_MCP_OIDC_ISSUER"),
        oidc_jwks_uri=_required_env("RAG_MCP_OIDC_JWKS_URI"),
        oidc_allowed_audiences=_required_csv_env("RAG_MCP_OIDC_ALLOWED_AUDIENCES"),
        required_scopes=_optional_csv_env("RAG_MCP_REQUIRED_SCOPES"),
        resource_server_url=_required_env("RAG_MCP_RESOURCE_SERVER_URL"),
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


def _required_csv_env(name: str) -> list[str]:
    """Lit une variable CSV obligatoire et retire les valeurs vides."""
    values = _optional_csv_env(name)
    if not values:
        raise McpConfigError(f"Variable d'environnement manquante : {name}")
    return values


def _optional_csv_env(name: str) -> list[str]:
    """Lit une variable CSV optionnelle et retourne une liste normalisée."""
    value = os.getenv(name, "")
    return [item.strip() for item in value.split(",") if item.strip()]
