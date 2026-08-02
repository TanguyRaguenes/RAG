import logging

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent

from app.core.config import load_mcp_config
from app.core.errors import McpAuthError, McpConfigError, McpError
from app.core.logging import configure_json_logging
from app.core.token_verifier import PocketIdTokenVerifier
from app.dal.clients.rag_client import RagClient
from app.services.documentation_service import DocumentationService

configure_json_logging("rag_mcp")
logger = logging.getLogger(__name__)

try:
    config = load_mcp_config()
except McpConfigError as error:
    logger.exception(
        "MCP configuration rejected",
        extra={
            "service": "rag_mcp",
            "event": "bootstrap_configuration_error",
            "error_code": error.code,
            "details": error.safe_details,
        },
    )
    raise

logger.info(
    "MCP configuration loaded",
    extra={
        "service": "rag_mcp",
        "event": "bootstrap_configuration_loaded",
        "audience_count": len(config.oidc_allowed_audiences),
        "required_scope_count": len(config.required_scopes),
    },
)

AUTH_SETTINGS = AuthSettings(
    issuer_url=config.oidc_issuer,
    required_scopes=list(config.required_scopes),
    resource_server_url=config.resource_server_url,
)
TRANSPORT_SECURITY = TransportSecuritySettings(
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
)


def _create_mcp_server() -> MCPServer:
    server = MCPServer(
        "RAG Entreprise",
        auth=AUTH_SETTINGS,
        token_verifier=PocketIdTokenVerifier(config),
    )
    return server


mcp = _create_mcp_server()
documentation_service = DocumentationService(RagClient(config))
TOOL_DESCRIPTION = """
Recherche dans le RAG documentaire interne de l'entreprise.

Utilise cet outil pour retrouver des informations dans les wikis et
documentations techniques internes. L'outil retourne les chunks documentaires les
plus pertinents avec leurs métadonnées, scores et chemins de fichiers. Il ne
génère pas directement une réponse finale : l'appelant doit synthétiser les
chunks retournés pour répondre à l'utilisateur.

Ne pas utiliser cet outil pour des questions générales sans lien avec la
documentation interne.
""".strip()


@mcp.tool(description=TOOL_DESCRIPTION)
async def interroger_documentation_interne(question: str) -> CallToolResult:
    """Recherche des chunks dans la documentation interne via le RAG.

    L'outil transmet la question utilisateur à l'orchestrator RAG avec le bearer
    token MCP courant, puis retourne les chunks récupérés. Le résultat sert de
    contexte documentaire à synthétiser par l'appelant.

    Args:
        question: Question utilisateur à rechercher dans la documentation
            interne. Ne pas inclure de secrets, tokens, mots de passe ou données
            sensibles.

    Returns:
        Résultat MCP contenant le même texte de succès qu'auparavant ou une erreur
        structurée avec `isError=true`.
    """
    try:
        access_token = get_access_token()
        if access_token is None:
            raise McpAuthError()

        answer = await documentation_service.answer(question, access_token.token)
        return _success_tool_result(answer)

    except McpError as error:
        _log_mcp_error(error)
        return _error_tool_result(error)
    except Exception as exception:
        logger.exception(
            "Erreur inattendue MCP",
            extra={
                "service": "rag_mcp",
                "event": "unexpected_error",
                "error_type": type(exception).__name__,
            },
        )
        error = McpError()
        return _error_tool_result(error)


def _success_tool_result(answer: str) -> CallToolResult:
    """Conserve le texte et le résultat structuré historique d'un succès.

    Args:
        answer: Texte JSON ou message d'absence de résultat produit par le service.

    Returns:
        Résultat MCP de succès compatible avec le SDK installé.
    """
    return CallToolResult(
        content=[TextContent(text=answer)],
        structuredContent={"result": answer},
    )


def _error_tool_result(error: McpError) -> CallToolResult:
    """Construit un échec d'outil MCP assaini et réellement signalé au protocole.

    Args:
        error: Erreur applicative déjà dépourvue de contenu sensible.

    Returns:
        Résultat avec `isError=true` et contrat d'erreur structuré.
    """
    return CallToolResult(
        content=[TextContent(text=error.public_message)],
        structuredContent={
            "result": error.public_message,
            "error": error.to_public_dict(),
        },
        isError=True,
    )


def _log_mcp_error(error: McpError) -> None:
    """Journalise une erreur attendue au niveau adapté, sans traceback sensible.

    Args:
        error: Erreur applicative classifiée par la frontière concernée.
    """
    level = (
        logging.WARNING
        if error.retryable or isinstance(error, McpAuthError)
        else logging.ERROR
    )
    logger.log(
        level,
        "MCP tool call failed",
        extra={
            "service": "rag_mcp",
            "event": "mcp_tool_error",
            "error_code": error.code,
            "retryable": error.retryable,
            "details": error.safe_details,
        },
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        transport_security=TRANSPORT_SECURITY,
    )
