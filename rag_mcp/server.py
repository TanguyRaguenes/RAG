import json
import os
import time

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RAG Entreprise")

RAG_ORCHESTRATOR_URL = os.environ["RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL"]

OIDC_TOKEN_URL = os.environ["RAG_MCP_OIDC_TOKEN_URL"]
OIDC_CLIENT_ID = os.environ["RAG_MCP_OIDC_CLIENT_ID"]
OIDC_CLIENT_SECRET = os.environ["RAG_MCP_OIDC_CLIENT_SECRET"]

_token_cache: dict[str, str | int] = {}


async def get_access_token() -> str:
    now = int(time.time())

    if (
        "access_token" in _token_cache
        and int(_token_cache.get("expires_at", 0)) > now + 30
    ):
        return str(_token_cache["access_token"])

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            OIDC_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": OIDC_CLIENT_ID,
                "client_secret": OIDC_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        response.raise_for_status()
        token_response = response.json()

    access_token = token_response["access_token"]
    expires_in = int(token_response.get("expires_in", 3600))

    _token_cache["access_token"] = access_token
    _token_cache["expires_at"] = now + expires_in

    return access_token


@mcp.tool()
async def interroger_documentation_interne(question: str) -> str:
    """
    Pose une question à la documentation interne.
    Retourne les données brutes JSON des chunks trouvés.
    """
    payload = {"question": question}

    try:
        access_token = await get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                RAG_ORCHESTRATOR_URL,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            data = response.json()
            retrieved_chunks = data.get("retrieved_chunks", [])

            if not retrieved_chunks:
                return "Aucune information trouvée."

            return json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        return (
            f"Erreur HTTP lors de l'appel au RAG : "
            f"{e.response.status_code} - {e.response.text}"
        )

    except httpx.RequestError as e:
        return f"Erreur réseau lors de l'appel au RAG : {str(e)}"

    except Exception as e:
        return f"Erreur inattendue : {str(e)}"


if __name__ == "__main__":
    mcp.settings.port = 8000
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport="sse")