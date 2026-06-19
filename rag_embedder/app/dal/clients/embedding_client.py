import httpx
import logging
import time
from opentelemetry import trace

from app.core.exceptions import EmbeddingServiceException
from app.core.metrics import (
    embedding_duration_seconds,
    embedding_errors_total,
    embedding_requests_total,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def embed_text(text: str, config: dict, is_query: bool) -> list[float]:
    embedding_requests_total.inc()
    start_time = time.perf_counter()

    url: str = config["embedding"]["url"]
    model: str = config["embedding"]["model"]
    prefix_query: str = config["embedding"]["prefixes"]["query"]
    prefix_document: str = config["embedding"]["prefixes"]["document"]

    logger.info(
        "Embedding request started",
        extra={
            "group": "embedding",
            "event": "request_started",
            "is_query": is_query,
            "text_length": len(text),
            "model": model,
        },
    )

    text_to_embed = f"{prefix_query}{text}" if is_query else f"{prefix_document}{text}"
    payload = {"model": model, "input": text_to_embed}

    try:
        with tracer.start_as_current_span("embedding.call_model") as span:
            span.set_attribute("embedding.model", model)
            span.set_attribute("embedding.is_query", is_query)
            span.set_attribute("embedding.text_length", len(text))
            span.set_attribute("http.url", url)

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

    except httpx.HTTPStatusError as e:
        embedding_errors_total.inc()
        logger.exception(
            "Embedding request failed",
            extra={
                "group": "embedding",
                "event": "request_failed",
                "error_type": "http_status",
                "status_code": e.response.status_code,
                "url": str(e.request.url),
            },
        )
        raise EmbeddingServiceException(
            message=f"Erreur HTTP {e.response.status_code}",
            details={"url": str(e.request.url), "response": e.response.text},
        ) from e

    except httpx.ConnectError as e:
        embedding_errors_total.inc()
        logger.exception(
            "Embedding request failed",
            extra={
                "group": "embedding",
                "event": "request_failed",
                "error_type": "connect_error",
                "url": url,
                "error": str(e),
            },
        )
        raise EmbeddingServiceException(
            message="Impossible de se connecter au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    except httpx.TimeoutException as e:
        embedding_errors_total.inc()
        logger.exception(
            "Embedding request failed",
            extra={
                "group": "embedding",
                "event": "request_failed",
                "error_type": "timeout",
                "url": url,
                "error": str(e),
            },
        )
        raise EmbeddingServiceException(
            message="Timeout lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    except httpx.RequestError as e:
        embedding_errors_total.inc()
        logger.exception(
            "Embedding request failed",
            extra={
                "group": "embedding",
                "event": "request_failed",
                "error_type": "request_error",
                "url": url,
                "error": str(e),
            },
        )
        raise EmbeddingServiceException(
            message="Erreur réseau lors de l'appel au service 'embedder'",
            details={"url": url, "error": str(e)},
        ) from e

    duration_seconds = time.perf_counter() - start_time
    duration_ms = round(duration_seconds * 1000, 2)

    embedding_duration_seconds.observe(duration_seconds)

    logger.info(
        "Embedding request completed",
        extra={
            "group": "embedding",
            "event": "request_completed",
            "duration_ms": duration_ms,
            "model": model,
            "embedding_size": len(data["embeddings"][0]),
        },
    )

    return data["embeddings"][0]
