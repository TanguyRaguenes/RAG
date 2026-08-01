import logging
import math
import time
from numbers import Real

import httpx
from opentelemetry import trace

from app.core.config import EmbedderConfig
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


async def embed(
    texts: list[str], config: EmbedderConfig, is_query: bool
) -> list[list[float]]:
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
        raise EmbeddingServiceException(
            internal_details={
                "operation": "embed",
                "error_type": "http_status",
                "status_code": e.response.status_code,
            },
        ) from e

    except httpx.ConnectError as e:
        embedding_errors_total.inc()
        _record_request_error(operation, "connect_error", start_time)
        raise EmbeddingServiceException(
            internal_details={"operation": "embed", "error_type": "connect_error"},
        ) from e

    except httpx.TimeoutException as e:
        embedding_errors_total.inc()
        _record_request_error(operation, "timeout", start_time)
        raise EmbeddingServiceException(
            internal_details={"operation": "embed", "error_type": "timeout"},
        ) from e

    except httpx.RequestError as e:
        embedding_errors_total.inc()
        _record_request_error(operation, "request_error", start_time)
        raise EmbeddingServiceException(
            internal_details={"operation": "embed", "error_type": "request_error"},
        ) from e

    except (TypeError, ValueError) as exception:
        embedding_errors_total.inc()
        _record_request_error(operation, "invalid_response", start_time)
        raise EmbeddingServiceException(
            internal_details={
                "operation": "embed",
                "error_type": "invalid_response",
            },
        ) from exception

    try:
        embeddings = _validate_embeddings(data["embeddings"], len(texts))
    except (KeyError, TypeError, ValueError) as exception:
        embedding_errors_total.inc()
        _record_request_error(operation, "invalid_response", start_time)
        raise EmbeddingServiceException(
            internal_details={
                "operation": "embed",
                "error_type": "invalid_response",
            },
        ) from exception

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
            "embedding_count": len(embeddings),
            "embedding_size": len(embeddings[0]),
        },
    )

    return embeddings


def _validate_embeddings(
    raw_embeddings: object, expected_count: int
) -> list[list[float]]:
    """Valide et normalise les embeddings retournés par le provider.

    Args:
        raw_embeddings: Valeur JSON brute du champ `embeddings`.
        expected_count: Nombre de vecteurs attendu pour les textes envoyés.

    Returns:
        Vecteurs composés exclusivement de nombres réels finis convertis en float.

    Raises:
        ValueError: Si le lot est désaligné, mal dimensionné ou contient une
            coordonnée NaN ou infinie.
        TypeError: Si une coordonnée n'est pas un nombre réel ou est booléenne.
    """
    if not isinstance(raw_embeddings, list) or len(raw_embeddings) != expected_count:
        raise ValueError("embedding response is not aligned with input texts")

    validated_embeddings: list[list[float]] = []
    for vector in raw_embeddings:
        if not isinstance(vector, list) or not vector:
            raise ValueError("embedding vectors must be non-empty lists")

        validated_vector: list[float] = []
        for coordinate in vector:
            if isinstance(coordinate, bool) or not isinstance(coordinate, Real):
                raise TypeError("embedding coordinates must be real numbers")
            try:
                normalized_coordinate = float(coordinate)
            except (OverflowError, ValueError) as exception:
                raise ValueError(
                    "embedding coordinates must be finite real numbers"
                ) from exception
            if not math.isfinite(normalized_coordinate):
                raise ValueError("embedding coordinates must be finite real numbers")
            validated_vector.append(normalized_coordinate)
        validated_embeddings.append(validated_vector)

    dimensions = {len(vector) for vector in validated_embeddings}
    if len(dimensions) != 1:
        raise ValueError("embedding dimensions are inconsistent")
    return validated_embeddings


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
