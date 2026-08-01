import os
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import DependencyResponseError, RerankerContainerException
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
        DependencyResponseError: Si la réponse JSON ne contient pas les chunks attendus.
    """
    url = os.getenv("RAG_RERANKER_RERANK_CHUNKS_URL")
    if not url:
        raise RerankerContainerException(
            internal_message="Reranker URL is not configured",
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
            raise RerankerContainerException(
                internal_message="Reranker returned an HTTP error",
                details={"status_code": exception.response.status_code},
            ) from exception
        except httpx.ConnectError as exception:
            _record_external_error("reranker", "rerank_chunks", "connect_error", start)
            raise RerankerContainerException(
                internal_message="Reranker connection failed",
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("reranker", "rerank_chunks", "timeout", start)
            raise RerankerContainerException(
                internal_message="Reranker request timed out",
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error("reranker", "rerank_chunks", "request_error", start)
            raise RerankerContainerException(
                internal_message="Reranker request failed",
            ) from exception
        except ValueError as exception:
            _record_external_error("reranker", "rerank_chunks", "invalid_json", start)
            raise DependencyResponseError(
                "Reranker returned invalid JSON",
                details={"dependency": "reranker", "operation": "rerank_chunks"},
            ) from exception

    try:
        reranked_chunks = _extract_reranked_chunks(data)
    except DependencyResponseError:
        _record_external_error("reranker", "rerank_chunks", "invalid_response", start)
        raise

    orchestrator_external_call_duration_seconds.labels(
        dependency="reranker", operation="rerank_chunks", status="success"
    ).observe(time.perf_counter() - start)
    return reranked_chunks


def _extract_reranked_chunks(data: object) -> list[dict[str, Any]]:
    """Valide le champ ``reranked_chunks`` d'une réponse reranker.

    Args:
        data: JSON décodé retourné par le reranker.

    Returns:
        Liste de chunks rerankés représentés par des objets JSON.

    Raises:
        DependencyResponseError: Si le champ est absent ou mal typé.
    """
    if not isinstance(data, dict):
        raise DependencyResponseError(
            "Reranker response is not an object",
            details={"dependency": "reranker", "operation": "rerank_chunks"},
        )

    try:
        chunks = data["reranked_chunks"]
    except (KeyError, TypeError) as exception:
        raise DependencyResponseError(
            "Reranker response is missing reranked_chunks",
            details={"dependency": "reranker", "operation": "rerank_chunks"},
        ) from exception

    if not isinstance(chunks, list) or not all(
        isinstance(chunk, dict) and isinstance(chunk.get("metadata", {}), dict)
        for chunk in chunks
    ):
        raise DependencyResponseError(
            "Reranker response contains malformed chunks",
            details={"dependency": "reranker", "operation": "rerank_chunks"},
        )
    return chunks


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
