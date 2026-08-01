import time
from collections.abc import Iterator
from contextlib import contextmanager

from opentelemetry import trace

from app.core.metrics import (
    SERVICE_NAME,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
    retriever_duration_seconds,
    retriever_errors_total,
    retriever_requests_total,
)

tracer = trace.get_tracer(__name__)


@contextmanager
def observe_retriever_operation(operation: str) -> Iterator[None]:
    """Mesure uniformément une opération appelée par une route FastAPI.

    Args:
        operation: Nom stable utilisé dans les spans et métriques.

    Yields:
        Contrôle au traitement de route entouré par l'observabilité.
    """
    start = time.perf_counter()
    with tracer.start_as_current_span(f"retriever.{operation}"):
        try:
            yield
        except Exception as exception:
            _record_error(operation, type(exception).__name__, start)
            raise
    _record_success(operation, start)


def _record_success(operation: str, start: float) -> None:
    """Enregistre les métriques d'une opération réussie.

    Args:
        operation: Nom stable de l'opération métier.
        start: Instant initial issu de `perf_counter`.
    """
    duration_seconds = time.perf_counter() - start
    retriever_requests_total.labels(operation=operation, status="success").inc()
    retriever_duration_seconds.labels(operation=operation, status="success").observe(
        duration_seconds
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(duration_seconds)


def _record_error(operation: str, error_type: str, start: float) -> None:
    """Enregistre les métriques d'une opération échouée.

    Args:
        operation: Nom stable de l'opération métier.
        error_type: Nom de classe de l'exception, à faible cardinalité.
        start: Instant initial issu de `perf_counter`.
    """
    duration_seconds = time.perf_counter() - start
    retriever_requests_total.labels(operation=operation, status="error").inc()
    retriever_errors_total.labels(operation=operation, error_type=error_type).inc()
    retriever_duration_seconds.labels(operation=operation, status="error").observe(
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
