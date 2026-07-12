import os
import time

import httpx
from opentelemetry import trace

from app.core.exceptions import EmbedderContainerException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def embed(texts: list[str]) -> list[list[float]]:
    """Génère les embeddings via le service embedder.

    Args:
        texts: Textes à vectoriser sans les logger.

    Returns:
        Liste d'embeddings retournés par `rag_embedder`.

    Raises:
        EmbedderContainerException: Si l'URL manque, si le service échoue, ou si l'appel HTTP échoue.
        KeyError: Si la réponse JSON ne contient pas `embeded_texts`.
    """
    url = os.getenv("RAG_EMBEDDER_EMBED_URL")
    if not url:
        raise EmbedderContainerException(
            message="URL du service 'embedder' non configurée",
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
            try:
                response_json = exception.response.json()
                raise EmbedderContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                    original_exception=response_json,
                ) from exception
            except ValueError:
                raise EmbedderContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("embedder", "embed", "connect_error", start)
            raise EmbedderContainerException(
                message="Impossible de se connecter au service 'embedder'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("embedder", "embed", "timeout", start)
            raise EmbedderContainerException(
                message="Timeout lors de l'appel au service 'embedder'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("embedder", "embed", "request_error", start)
            raise EmbedderContainerException(
                message="Erreur réseau lors de l'appel au service 'embedder'",
                details={"url": url, "error": str(exception)},
            ) from exception

    orchestrator_external_call_duration_seconds.labels(
        dependency="embedder", operation="embed", status="success"
    ).observe(time.perf_counter() - start)

    return data["embeded_texts"]


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
