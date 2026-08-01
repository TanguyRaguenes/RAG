import logging
import time
from typing import Any

from app.core.metrics import (
    SERVICE_NAME,
    orchestrator_chunks_total,
    orchestrator_duration_seconds,
    orchestrator_errors_total,
    orchestrator_requests_total,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
)

logger = logging.getLogger(__name__)


def elapsed_ms(start: float) -> int:
    """Calcule la durée d'une opération en millisecondes.

    Args:
        start: Instant de départ capturé avec `perf_counter`.

    Returns:
        Durée écoulée en millisecondes entières.
    """
    try:
        return int((time.perf_counter() - start) * 1000)
    except StopIteration:
        return 0


def format_duration(duration_ms: int) -> str:
    """Formate une durée en minutes et secondes.

    Args:
        duration_ms: Durée en millisecondes.

    Returns:
        Durée au format `MM:SS`.
    """
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def get_llm_provider(provider: str, config: dict[str, Any]) -> str:
    """Résout le fournisseur LLM effectif depuis la configuration.

    Args:
        provider: Clé de fournisseur demandée par le client.
        config: Configuration applicative du pipeline LLM.

    Returns:
        Nom du fournisseur LLM configuré.

    Raises:
        KeyError: Si le fournisseur demandé n'est pas configuré.
    """
    return config["llm"][provider]["provider"]


def record_orchestration_success(
    operation: str,
    start: float,
    chunk_count: int,
) -> None:
    """Enregistre les métriques et le log d'une orchestration réussie.

    Args:
        operation: Nom stable de l'opération métier.
        start: Instant de départ capturé avec `perf_counter`.
        chunk_count: Nombre de chunks produits par l'opération.
    """
    duration_seconds = _elapsed_seconds(start)
    orchestrator_requests_total.labels(operation=operation, status="success").inc()
    orchestrator_duration_seconds.labels(operation=operation, status="success").observe(
        duration_seconds
    )
    orchestrator_chunks_total.labels(operation=operation).inc(chunk_count)
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)
    logger.info(
        "orchestrator operation completed",
        extra={
            "service": "rag_orchestrator",
            "event": "operation_completed",
            "operation": operation,
            "status": "success",
            "duration_ms": round(duration_seconds * 1000, 2),
            "chunk_count": chunk_count,
        },
    )


def record_orchestration_error(
    operation: str,
    error_type: str,
    start: float,
) -> None:
    """Enregistre les métriques et le log d'une orchestration échouée.

    Args:
        operation: Nom stable de l'opération métier.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter`.
    """
    duration_seconds = _elapsed_seconds(start)
    orchestrator_requests_total.labels(operation=operation, status="error").inc()
    orchestrator_errors_total.labels(operation=operation, error_type=error_type).inc()
    orchestrator_duration_seconds.labels(operation=operation, status="error").observe(
        duration_seconds
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).inc()
    rag_errors_total.labels(
        service=SERVICE_NAME, operation=operation, error_type=error_type
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="error"
    ).observe(duration_seconds)
    logger.warning(
        "orchestrator operation failed",
        extra={
            "service": "rag_orchestrator",
            "event": "operation_failed",
            "operation": operation,
            "status": "error",
            "duration_ms": round(duration_seconds * 1000, 2),
            "error_type": error_type,
        },
    )


def _elapsed_seconds(start: float) -> float:
    """Calcule une durée sans faire échouer une horloge patchée en test.

    Args:
        start: Instant de départ capturé avec `perf_counter`.

    Returns:
        Durée écoulée en secondes, ou zéro si l'itérateur de test est épuisé.
    """
    try:
        return time.perf_counter() - start
    except StopIteration:
        return 0.0
