import os

import httpx

from app.core.exceptions import RetrievalServiceException
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_store_items_schema import VectorStoreItemsBase


async def save_items(
    vector_store_items: VectorStoreItemsBase,
) -> SaveItemsResponseBase:
    """Envoie les items vectoriels au service retriever pour persistance.

    Args:
        vector_store_items: Items vectoriels préparés par l'embedder pour être sauvegardés par le retriever.

    Returns:
        Réponse du retriever décrivant les items sauvegardés.

    Raises:
        RetrievalServiceException: Si le service retriever ne peut pas sauvegarder les embeddings.
    """
    url = os.getenv("RAG_RETRIEVER_INGEST_DOCUMENTS_URL")
    if not url:
        raise RetrievalServiceException(
            internal_details={"operation": "save_items", "error_type": "missing_url"},
        )

    payload = vector_store_items.model_dump()

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RetrievalServiceException(
                internal_details={
                    "operation": "save_items",
                    "error_type": "http_status",
                    "status_code": e.response.status_code,
                },
            ) from e
        except httpx.ConnectError as e:
            raise RetrievalServiceException(
                internal_details={
                    "operation": "save_items",
                    "error_type": "connect_error",
                },
            ) from e
        except httpx.TimeoutException as e:
            raise RetrievalServiceException(
                internal_details={"operation": "save_items", "error_type": "timeout"},
            ) from e
        except httpx.RequestError as e:
            raise RetrievalServiceException(
                internal_details={
                    "operation": "save_items",
                    "error_type": "request_error",
                },
            ) from e

    try:
        return SaveItemsResponseBase.model_validate(resp.json())
    except (ValueError, TypeError) as exception:
        raise RetrievalServiceException(
            internal_details={
                "operation": "save_items",
                "error_type": "invalid_response",
            },
        ) from exception
