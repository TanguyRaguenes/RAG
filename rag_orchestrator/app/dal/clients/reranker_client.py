import os
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import RerankerContainerException
from app.core.metrics import (
    orchestrator_external_call_duration_seconds,
    orchestrator_external_call_errors_total,
)

tracer = trace.get_tracer(__name__)


async def rerank_chunks(
    question: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Réordonne les chunks via le service reranker.

    Args:
        question: Question utilisateur transmise au reranker, sans la logger.
        chunks: Chunks candidats issus du retriever.

    Returns:
        Liste de chunks enrichis et triés par score de reranking.

    Raises:
        RerankerContainerException: Si l'URL manque, si le reranker échoue, ou si l'appel HTTP échoue.
        KeyError: Si la réponse JSON ne contient pas `reranked_chunks`.
    """
    url = os.getenv("RAG_RERANKER_RERANK_CHUNKS_URL")
    if not url:
        raise RerankerContainerException(
            message="URL du service 'reranker' non configurée",
            details={"env_var": "RAG_RERANKER_RERANK_CHUNKS_URL"},
        )

    payload = {"question": question, "chunks": chunks}
    start = time.perf_counter()

    with tracer.start_as_current_span("orchestrator.call_reranker") as span:
        span.set_attribute("dependency", "rag_reranker")
        span.set_attribute("operation", "rerank_chunks")
        span.set_attribute("chunk_count", len(chunks))

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error("reranker", "rerank_chunks", "http_status", start)
            try:
                response_json = exception.response.json()
                raise RerankerContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                    original_exception=response_json,
                ) from exception
            except ValueError:
                raise RerankerContainerException(
                    message=f"Erreur HTTP {exception.response.status_code}",
                    details={"url": url, "error": str(exception)},
                ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("reranker", "rerank_chunks", "connect_error", start)
            raise RerankerContainerException(
                message="Impossible de se connecter au service 'reranker'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("reranker", "rerank_chunks", "timeout", start)
            raise RerankerContainerException(
                message="Timeout lors de l'appel au service 'reranker'",
                details={"url": url, "error": str(exception)},
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("reranker", "rerank_chunks", "request_error", start)
            raise RerankerContainerException(
                message="Erreur réseau lors de l'appel au service 'reranker'",
                details={"url": url, "error": str(exception)},
            ) from exception

    orchestrator_external_call_duration_seconds.labels(
        dependency="reranker", operation="rerank_chunks", status="success"
    ).observe(time.perf_counter() - start)

    return data["reranked_chunks"]


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
