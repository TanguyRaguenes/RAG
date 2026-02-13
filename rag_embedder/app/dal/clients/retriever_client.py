import os
from typing import Any

import httpx

from app.core.exceptions import RetrievalServiceException
from app.domain.models.vector_store_item_model import VectorStoreItemsBase


async def save_items(vector_store_items: VectorStoreItemsBase) -> Any:
    url = os.getenv("RAG_RETRIEVER_INGEST_DOCUMENTS_URL")
    if not url:
        raise RetrievalServiceException(
            message="Le endpoint du service 'retriever' permettant l'ingestion des documents n'est pas renseigné.",
            details={
                "action": "renseigner la variable d'environnement dans le fichier docker-compose.yml"
            },
        )

    payload = vector_store_items.model_dump()

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RetrievalServiceException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": str(e.request.url), "response": e.response.text},
            ) from e
        except httpx.ConnectError as e:
            raise RetrievalServiceException(
                message="Impossible de se connecter au service 'retriever'",
                details={"url": url, "error": str(e)},
            ) from e
        except httpx.TimeoutException as e:
            raise RetrievalServiceException(
                message="Timeout lors de l'appel au service 'retriever'",
                details={"url": url, "error": str(e)},
            ) from e
        except httpx.RequestError as e:
            raise RetrievalServiceException(
                message="Erreur réseau lors de l'appel au service 'retriever'",
                details={"url": url, "error": str(e)},
            ) from e

    data = resp.json()

    return data
