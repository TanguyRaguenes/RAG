import json

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("RAG Entreprise")
RAG_API_URL = "http://rag_api:8000/retrieve_chunks"


@mcp.tool()
async def interroger_documentation_interne(question: str) -> str:
    """
    Pose une question à la documentation interne.
    Retourne les données brutes (JSON) des chunks trouvés.
    """
    payload = {"question": question}

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(RAG_API_URL, json=payload)
            response.raise_for_status()

            data = response.json()
            retrieved_chunks = data.get("retrieved_chunks", [])

            if not retrieved_chunks:
                return "Aucune information trouvée."

            # ensure_ascii=False permet de garder les accents lisibles
            # indent=2 rend le JSON plus lisible pour l'humain si besoin
            return json.dumps(retrieved_chunks, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Erreur : {str(e)}"


if __name__ == "__main__":
    mcp.settings.port = 8000
    mcp.settings.host = "0.0.0.0"
    mcp.run(transport="sse")
