import httpx
from mcp.server.fastmcp import FastMCP

from auth_client import get_access_token
from config import load_mcp_config
from rag_client import retrieve_documentation_chunks

mcp = FastMCP("RAG Entreprise")


@mcp.tool()
async def interroger_documentation_interne(question: str) -> str:
    """
    Pose une question à la documentation interne.
    Retourne les données brutes JSON des chunks trouvés.
    """
    try:
        config = load_mcp_config()
        access_token = await get_access_token(config)

        return await retrieve_documentation_chunks(
            config=config,
            question=question,
            access_token=access_token,
        )

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
