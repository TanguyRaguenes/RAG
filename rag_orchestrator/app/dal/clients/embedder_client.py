import os
import time

import httpx
from opentelemetry import trace

from app.core.exceptions import DependencyResponseError, EmbedderContainerException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def embed(texts: list[str]) -> tuple[list[list[float]], bool]:
    """Génère les embeddings via le service embedder.

    Args:
        texts: Textes à vectoriser sans les logger.

    Returns:
        Embeddings et état actuel du chunking retournés par `rag_embedder`.

    Raises:
        EmbedderContainerException: Si l'URL manque, si le service échoue, ou si l'appel HTTP échoue.
        DependencyResponseError: Si la réponse JSON ne contient pas les embeddings attendus.
    """
    url = os.getenv("RAG_EMBEDDER_EMBED_URL")
    if not url:
        raise EmbedderContainerException(
            internal_message="Embedder URL is not configured",
            details={"env_var": "RAG_EMBEDDER_EMBED_URL"},
        )

    payload = {"texts": texts}
    start = time.perf_counter()

    with tracer.start_as_current_span("orchestrator.call_embedder") as span:
        span.set_attribute("dependency", "rag_embedder")
        span.set_attribute("operation", "embed")
        span.set_attribute("text_count", len(texts))

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error("embedder", "embed", "http_status", start)
            raise EmbedderContainerException(
                internal_message="Embedder returned an HTTP error",
                details={"status_code": exception.response.status_code},
            ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("embedder", "embed", "connect_error", start)
            raise EmbedderContainerException(
                internal_message="Embedder connection failed",
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("embedder", "embed", "timeout", start)
            raise EmbedderContainerException(
                internal_message="Embedder request timed out",
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("embedder", "embed", "request_error", start)
            raise EmbedderContainerException(
                internal_message="Embedder request failed",
            ) from exception
        except ValueError as exception:
            _record_external_error("embedder", "embed", "invalid_json", start)
            raise DependencyResponseError(
                "Embedder returned invalid JSON",
                details={"dependency": "embedder", "operation": "embed"},
            ) from exception

    try:
        embeddings, chunking_enabled = _extract_embedding_result(data)
    except DependencyResponseError:
        _record_external_error("embedder", "embed", "invalid_response", start)
        raise

    orchestrator_external_call_duration_seconds.labels(
        dependency="embedder", operation="embed", status="success"
    ).observe(time.perf_counter() - start)
    return embeddings, chunking_enabled


def _extract_embedding_result(data: object) -> tuple[list[list[float]], bool]:
    """Valide les embeddings et la configuration retournés par l'embedder.

    Args:
        data: JSON décodé retourné par la dépendance.

    Returns:
        Liste non vide d'embeddings numériques et état actuel du chunking.

    Raises:
        DependencyResponseError: Si la structure de réponse est absente ou malformée.
    """
    if not isinstance(data, dict):
        raise DependencyResponseError(
            "Embedder response is not an object",
            details={"dependency": "embedder", "operation": "embed"},
        )

    try:
        embeddings = data["embeded_texts"]
        chunking_enabled = data["chunking_enabled"]
    except (KeyError, TypeError) as exception:
        raise DependencyResponseError(
            "Embedder response is missing required fields",
            details={"dependency": "embedder", "operation": "embed"},
        ) from exception

    if (
        not isinstance(embeddings, list)
        or not embeddings
        or not all(
            isinstance(embedding, list)
            and embedding
            and all(
                not isinstance(value, bool) and isinstance(value, int | float)
                for value in embedding
            )
            for embedding in embeddings
        )
    ):
        raise DependencyResponseError(
            "Embedder response contains malformed embeddings",
            details={"dependency": "embedder", "operation": "embed"},
        )
    if not isinstance(chunking_enabled, bool):
        raise DependencyResponseError(
            "Embedder response contains invalid chunking configuration",
            details={"dependency": "embedder", "operation": "embed"},
        )
    return embeddings, chunking_enabled


def _record_external_error(
    dependency: str, operation: str, error_type: str, start: float
) -> None:
    """Enregistre une erreur d'appel externe.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    orchestrator_external_call_errors_total.labels(
        dependency=dependency, operation=operation, error_type=error_type
    ).inc()
    orchestrator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="error"
    ).observe(time.perf_counter() - start)
