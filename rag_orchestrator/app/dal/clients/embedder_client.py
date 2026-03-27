import os
from typing import Any

import httpx

from app.core.exceptions import EmbedderContainerException


async def embed_question(question: str) -> Any:
    url = os.getenv("RAG_EMBEDDER_EMBED_QUESTION_URL")

    payload = {"text": question}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        try:
            response_json = e.response.json()
            raise EmbedderContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
                original_exception=response_json,
            ) from e
        except ValueError:
            raise EmbedderContainerException(
                message=f"Erreur HTTP {e.response.status_code}",
                details={"url": url, "error": str(e)},
            ) from e
    except httpx.ConnectError as e:
        raise EmbedderContainerException(
            message="Impossible de se connecter au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        raise EmbedderContainerException(
            message="Timeout lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        # couvre DNS, reset, etc. (hors ConnectError/TimeoutException déjà traités)
        raise EmbedderContainerException(
            message="Erreur réseau lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    return data["embeded_text"]
