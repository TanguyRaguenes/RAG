import httpx
import logging
import time

from app.core.metrics import (
    embedding_duration_seconds,
    embedding_errors_total,
    embedding_requests_total,
)


from app.core.exceptions import EmbeddingServiceException


logger = logging.getLogger(__name__)


async def embed_text(text: str, config: dict, is_query: bool) -> list[float]:

    embedding_requests_total.inc()

    start_time = time.perf_counter()

    url: str = config["embedding"]["url"]
    model: str = config["embedding"]["model"]
    prefix_query: str = config["embedding"]["prefixes"]["query"]
    prefix_document: str = config["embedding"]["prefixes"]["document"]

    logger.info(
        "Embedding request started | is_query=%s | text_length=%s | model=%s | url=%s",
        is_query,
        len(text),
        model,
        url,
    )

    text_to_embed: str

    if is_query:
        text_to_embed = f"{prefix_query}{text}"
    else:
        text_to_embed = f"{prefix_document}{text}"

    payload = {"model": model, "input": text_to_embed}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        embedding_errors_total.inc()
        raise EmbeddingServiceException(
            message=f"Erreur HTTP {e.response.status_code}",
            details={"url": str(e.request.url), "response": e.response.text},
        ) from e
    except httpx.ConnectError as e:
        embedding_errors_total.inc()
        raise EmbeddingServiceException(
            message="Impossible de se connecter au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.TimeoutException as e:
        embedding_errors_total.inc()
        raise EmbeddingServiceException(
            message="Timeout lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e
    except httpx.RequestError as e:
        embedding_errors_total.inc()
        # couvre DNS, reset, etc. (hors ConnectError/TimeoutException déjà traités)
        raise EmbeddingServiceException(
            message="Erreur réseau lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    duration_seconds = time.perf_counter() - start_time

    embedding_duration_seconds.observe(duration_seconds)

    duration_ms = round(duration_seconds * 1000, 2)

    embedding_duration_seconds.observe(duration_seconds)

    logger.info(
        "Embedding request completed | duration_ms=%s",
        duration_ms,
    )

    return data["embeddings"][0]
