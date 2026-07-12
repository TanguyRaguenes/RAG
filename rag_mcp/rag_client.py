import json
from typing import Any

import httpx

from config import McpConfig, McpRagClientError


async def retrieve_documentation_chunks(
    *,
    config: McpConfig,
    question: str,
    access_token: str,
) -> str:
    """Récupère les chunks de documentation auprès de l'orchestrator.

    Args:
        config: Configuration MCP contenant l'URL orchestrator.
        question: Question reçue via l'outil MCP, non loggée.
        access_token: Token OIDC utilisé dans l'en-tête Authorization.

    Returns:
        Chaîne JSON formatée des chunks ou message d'absence de résultat.

    Raises:
        McpRagClientError: Si l'appel orchestrator échoue ou retourne un JSON invalide.
    """
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                config.rag_orchestrator_url,
                json={"question": question},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exception:
        raise McpRagClientError(
            "Erreur lors de l'appel à l'orchestrator",
            details={
                "url": config.rag_orchestrator_url,
                "error_type": type(exception).__name__,
            },
        ) from exception
    except ValueError as exception:
        raise McpRagClientError(
            "L'orchestrator a retourné un JSON invalide",
            details={"url": config.rag_orchestrator_url},
        ) from exception

    return format_retrieved_chunks_response(data)


def format_retrieved_chunks_response(data: dict[str, Any]) -> str:
    """Formate les chunks récupérés pour l'appelant MCP.

    Args:
        data: Réponse JSON de l'orchestrator.

    Returns:
        Chaîne JSON indentée des chunks ou message d'absence de résultat.
    """
    retrieved_chunks = data.get("retrieved_chunks", [])

    if not retrieved_chunks:
        return "Aucune information trouvée."

    return json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)
