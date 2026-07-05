import os
from dataclasses import dataclass


@dataclass(frozen=True)
class McpConfig:
    rag_orchestrator_url: str
    oidc_token_url: str
    oidc_client_id: str
    oidc_client_secret: str


class McpConfigError(RuntimeError):
    """Configuration obligatoire manquante pour le serveur MCP."""


def load_mcp_config() -> McpConfig:
    return McpConfig(
        rag_orchestrator_url=_required_env("RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL"),
        oidc_token_url=_required_env("RAG_MCP_OIDC_TOKEN_URL"),
        oidc_client_id=_required_env("RAG_MCP_OIDC_CLIENT_ID"),
        oidc_client_secret=_required_env("RAG_MCP_OIDC_CLIENT_SECRET"),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise McpConfigError(f"Variable d'environnement manquante : {name}")
    return value
