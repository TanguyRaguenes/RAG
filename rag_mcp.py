from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# 1. Création du serveur MCP
mcp = FastMCP("RAG Entreprise")

# 2. Configuration de l'URL pour poser une question au RAG
RAG_API_URL = "http://localhost:8003/retrieve_chunks"


# 3. Définition de l'outil pour l'Agent
@mcp.tool()
async def interroger_documentation_interne(question: str) -> list[dict[str, Any]]:
    """
    Pose une question à la documentation interne de l'entreprise via le RAG.
    Utilise cet outil dès que l'utilisateur pose une question sur :
    - Les procédures internes
    - La documentation technique
    - Les informations RH ou administratives
    """

    # On prépare la donnée à envoyer (correspond à votre schéma LlmRequestBase)
    payload = {"question": question}

    # On utilise un client HTTP asynchrone pour ne pas bloquer l'agent
    async with httpx.AsyncClient(timeout=360) as client:
        try:
            # Appel vers votre Docker (rag_api)
            response = await client.post(RAG_API_URL, json=payload)
            response.raise_for_status()

            data = response.json()

            return data["retrieved_chunks"]

        except httpx.ConnectError:
            return "Erreur : Impossible de joindre le RAG. Vérifiez que le conteneur 'rag_api' tourne bien et expose le port 8003."
        except Exception as e:
            return f"Erreur technique lors de l'appel au RAG : {str(e)}"


# 4. Lancement
if __name__ == "__main__":
    mcp.run()
