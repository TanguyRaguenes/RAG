import httpx
import logging
import time
from opentelemetry import trace

from app.core.exceptions import EmbeddingServiceException
from app.core.metrics import (
    SERVICE_NAME,
    embedding_duration_seconds,
    embedding_errors_total,
    embedding_requests_total,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def embed(texts: list[str], config: dict, is_query: bool) -> list[list[float]]:
    """Génère des embeddings pour une liste de textes via le client configuré.

    Args:
        texts: Textes à vectoriser ou normaliser.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        is_query: Indique si les textes représentent une requête utilisateur ou un document.

    Returns:
        Liste d'embeddings alignée avec les textes d'entrée.

    Raises:
        EmbeddingServiceException: Si le service d'embedding ou son provider ne répond pas correctement.
    """
    start_time = time.perf_counter()
    operation = "embed"
    embedding_requests_total.inc()

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
            "text_count": len(texts),
            "total_text_length": sum(len(text) for text in texts),
            "model": model,
        },
    )

    prefix = prefix_query if is_query else prefix_document
    texts_to_embed = [f"{prefix}{text}" for text in texts]
    payload = {"model": model, "input": texts_to_embed}

    try:
        with tracer.start_as_current_span("embedding.call_model") as span:
            span.set_attribute("embedding.model", model)
            span.set_attribute("embedding.is_query", is_query)
            span.set_attribute("embedding.text_count", len(texts))
            span.set_attribute(
                "embedding.total_text_length",
                sum(len(text) for text in texts),
            )
            span.set_attribute("http.url", url)

            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

    except httpx.HTTPStatusError as e:
        embedding_errors_total.inc()
        _record_request_error(operation, "http_status", start_time)
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
        _record_request_error(operation, "connect_error", start_time)
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
        _record_request_error(operation, "timeout", start_time)
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
        _record_request_error(operation, "request_error", start_time)
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
    _record_request_success(operation, duration_seconds)

    logger.info(
        "Embedding request completed",
        extra={
            "group": "embedding",
            "event": "request_completed",
            "duration_ms": duration_ms,
            "model": model,
            "embedding_count": len(data["embeddings"]),
            "embedding_size": len(data["embeddings"][0]),
        },
    )

    return data["embeddings"]


def _record_request_success(operation: str, duration_seconds: float) -> None:
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)


def _record_request_error(operation: str, error_type: str, start_time: float) -> None:
    duration_seconds = time.perf_counter() - start_time
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).inc()
    rag_errors_total.labels(
        service=SERVICE_NAME, operation=operation, error_type=error_type
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).observe(duration_seconds)
