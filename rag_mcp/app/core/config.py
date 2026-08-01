import os
from dataclasses import dataclass

from app.core.errors import McpConfigError

REQUIRED_MCP_SCOPE = "rag:mcp"


@dataclass(frozen=True)
class McpConfig:
    """Configuration nécessaire au serveur MCP."""

    rag_orchestrator_url: str
    oidc_issuer: str
    oidc_jwks_uri: str
    oidc_allowed_audiences: tuple[str, ...]
    required_scopes: tuple[str, ...]
    resource_server_url: str


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
        required_scopes=_mcp_required_scopes(),
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
        raise McpConfigError(safe_details={"configuration": name})
    return value


def _required_csv_env(name: str) -> tuple[str, ...]:
    """Lit une variable CSV obligatoire et retire les valeurs vides."""
    values = _optional_csv_env(name)
    if not values:
        raise McpConfigError(safe_details={"configuration": name})
    return values


def _optional_csv_env(name: str) -> tuple[str, ...]:
    """Lit une variable CSV optionnelle et retourne un tuple normalisé."""
    value = os.getenv(name, "")
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _mcp_required_scopes() -> tuple[str, ...]:
    """Garantit le scope métier MCP en complément des scopes configurés.

    Returns:
        Scopes exigés, avec `rag:mcp` toujours présent une seule fois.
    """
    configured_scopes = _optional_csv_env("RAG_MCP_REQUIRED_SCOPES")
    return (
        REQUIRED_MCP_SCOPE,
        *(scope for scope in configured_scopes if scope != REQUIRED_MCP_SCOPE),
    )
