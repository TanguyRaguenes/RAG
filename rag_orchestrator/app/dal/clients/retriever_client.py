import os
from typing import Any

import httpx

from app.core.exceptions import RetrieverContainerException


async def retrieve_chunks(embeded_question: list[float]) -> list[dict[str, Any]]:
    url = os.getenv("RAG_RETRIEVER_RETRIEVE_CHUNKS_URL")
    if not url:
        raise RetrieverContainerException(
            message="URL du service 'retriever' non configurée",
            details={"env_var": "RAG_RETRIEVER_RETRIEVE_CHUNKS_URL"},
        )

    payload = {"embeded_question": embeded_question}

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        try:
            response_json = e.response.json()
            raise RetrieverContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
                original_exception=response_json,
            ) from e
        except ValueError:
            raise RetrieverContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
            ) from e
    except httpx.ConnectError as e:
        raise RetrieverContainerException(
            message="Impossible de se connecter au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise RetrieverContainerException(
            message="Timeout lors de l'appel au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        raise RetrieverContainerException(
            message="Erreur réseau lors de l'appel au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e

    return data["chunks"]


async def retrieve_document_chunks(
    paths: list[str],
) -> list[dict[str, Any]]:
    url = os.getenv("RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL")
    if not url:
        raise RetrieverContainerException(
            message="URL du service 'retriever' non configurée",
            details={"env_var": "RAG_RETRIEVER_RETRIEVE_DOCUMENT_CHUNKS_URL"},
        )

    payload = {"paths": paths}

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        try:
            response_json = e.response.json()
            raise RetrieverContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
                original_exception=response_json,
            ) from e
        except ValueError:
            raise RetrieverContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
            ) from e
    except httpx.ConnectError as e:
        raise RetrieverContainerException(
            message="Impossible de se connecter au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise RetrieverContainerException(
            message="Timeout lors de l'appel au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        raise RetrieverContainerException(
            message="Erreur réseau lors de l'appel au service 'retriever'",
            details={"url": url, "error": str(e)},
        ) from e

    return data["chunks"]
