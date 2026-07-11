import os
from typing import Any

import httpx

from app.core.exceptions import RerankerContainerException


async def rerank_chunks(
    question: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    url = os.getenv("RAG_RERANKER_RERANK_CHUNKS_URL")
    if not url:
        raise RerankerContainerException(
            message="URL du service 'reranker' non configurée",
            details={"env_var": "RAG_RERANKER_RERANK_CHUNKS_URL"},
        )

    payload = {"question": question, "chunks": chunks}

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        try:
            response_json = e.response.json()
            raise RerankerContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
                original_exception=response_json,
            ) from e
        except ValueError:
            raise RerankerContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
            ) from e
    except httpx.ConnectError as e:
        raise RerankerContainerException(
            message="Impossible de se connecter au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise RerankerContainerException(
            message="Timeout lors de l'appel au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        raise RerankerContainerException(
            message="Erreur réseau lors de l'appel au service 'reranker'",
            details={"url": url, "error": str(e)},
        ) from e

    return data["reranked_chunks"]
