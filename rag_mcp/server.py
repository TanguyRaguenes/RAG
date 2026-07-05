import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RAG Entreprise")

_token_cache: dict[str, str | int] = {}


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


async def get_access_token(config: McpConfig | None = None) -> str:
    config = config or load_mcp_config()
    now = int(time.time())

    if is_cached_token_valid(_token_cache, now):
        return str(_token_cache["access_token"])

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            config.oidc_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": config.oidc_client_id,
                "client_secret": config.oidc_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response.raise_for_status()
        token_response = response.json()

    access_token = token_response["access_token"]
    expires_in = int(token_response.get("expires_in", 3600))

    cache_access_token(_token_cache, access_token, now + expires_in)

    return access_token


@mcp.tool()
async def interroger_documentation_interne(question: str) -> str:
    """
    Pose une question à la documentation interne.
    Retourne les données brutes JSON des chunks trouvés.
    """
    payload = {"question": question}

    try:
        config = load_mcp_config()
        access_token = await get_access_token(config)

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                config.rag_orchestrator_url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            return format_retrieved_chunks_response(response.json())

    except httpx.HTTPStatusError as e:
        return (
            f"Erreur HTTP lors de l'appel au RAG : "
            f"{e.response.status_code} - {e.response.text}"
        )

    except httpx.RequestError as e:
        return f"Erreur réseau lors de l'appel au RAG : {str(e)}"

    except Exception as e:
        return f"Erreur inattendue : {str(e)}"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise McpConfigError(f"Variable d'environnement manquante : {name}")
    return value


def is_cached_token_valid(cache: dict[str, str | int], now: int) -> bool:
    return "access_token" in cache and int(cache.get("expires_at", 0)) > now + 30


def cache_access_token(
    cache: dict[str, str | int], access_token: str, expires_at: int
) -> None:
    cache["access_token"] = access_token
    cache["expires_at"] = expires_at


def format_retrieved_chunks_response(data: dict[str, Any]) -> str:
    retrieved_chunks = data.get("retrieved_chunks", [])

    if not retrieved_chunks:
        return "Aucune information trouvée."

    return json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.settings.port = 8000
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport="sse")
