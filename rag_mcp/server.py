import logging

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings

from config import McpAuthError, McpError, load_mcp_config
from rag_client import retrieve_documentation_chunks
from token_verifier import PocketIdTokenVerifier

config = load_mcp_config()

mcp = FastMCP(
    "RAG Entreprise",
    auth=AuthSettings(
        issuer_url=config.oidc_issuer,
        required_scopes=config.required_scopes,
        resource_server_url=config.resource_server_url,
    ),
    token_verifier=PocketIdTokenVerifier(config),
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "mcp.isilograginterne.fr",
            "mcp.isilograginterne.fr:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "https://mcp.isilograginterne.fr",
        ],
    ),
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@mcp.tool()
async def interroger_documentation_interne(question: str) -> str:
    """Pose une question à la documentation interne.
    Retourne les données brutes JSON des chunks trouvés.

    Args:
        question: Question à transmettre au RAG, non loggée.

    Returns:
        Chaîne JSON des chunks récupérés ou message d'erreur exploitable par Kilo.
    """
    try:
        access_token = get_access_token()
        if access_token is None:
            raise McpAuthError("Token utilisateur MCP manquant")

        return await retrieve_documentation_chunks(
            config=config,
            question=question,
            access_token=access_token.token,
        )

    except McpError as exception:
        logger.exception(
            exception.message,
            extra={
                "service": "rag_mcp",
                "event": "mcp_error",
                "details": exception.details,
            },
        )
        return f"Erreur MCP : {exception.message}"
    except httpx.HTTPStatusError as exception:
        logger.exception(
            "Erreur HTTP non normalisée lors de l'appel MCP",
            extra={"service": "rag_mcp", "event": "http_status_error"},
        )
        return (
            f"Erreur HTTP lors de l'appel au RAG : "
            f"{exception.response.status_code} - {exception.response.text}"
        )
    except httpx.HTTPError as exception:
        logger.exception(
            "Erreur HTTP non normalisée lors de l'appel MCP",
            extra={
                "service": "rag_mcp",
                "event": "http_error",
                "error_type": type(exception).__name__,
            },
        )
        return "Erreur HTTP lors de l'appel au RAG."
    except Exception as exception:
        logger.exception(
            "Erreur inattendue MCP",
            extra={
                "service": "rag_mcp",
                "event": "unexpected_error",
                "error_type": type(exception).__name__,
            },
        )
        return "Erreur inattendue lors de l'appel au RAG."


if __name__ == "__main__":
    mcp.settings.port = 8000
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport="streamable-http")
