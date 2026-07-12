import os
import time
from typing import Any

import httpx
from opentelemetry import trace

from app.core.exceptions import EvaluatorClientError
from app.core.metrics import (
    evaluator_external_call_duration_seconds,
    evaluator_errors_total,
)

tracer = trace.get_tracer(__name__)


async def ask_question(question: str) -> dict[str, Any]:
    """Pose une question à l'orchestrator pour l'évaluation.

    Args:
        question: Question du dataset, non loggée pour éviter l'exposition de contenu.

    Returns:
        Réponse JSON décodée de `rag_orchestrator`.

    Raises:
        EvaluatorClientError: Si l'URL manque, si l'appel HTTP échoue ou si le format retourné est invalide.
    """
    rag_orchestrator_url = os.getenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL")
    if not rag_orchestrator_url:
        raise EvaluatorClientError(
            message="URL de l'orchestrator non configurée",
            details={"env_var": "RAG_ORCHESTRATOR_ASK_QUESTION_URL"},
        )

    start = time.perf_counter()
    with tracer.start_as_current_span("evaluator.call_orchestrator"):
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    rag_orchestrator_url,
                    json={"question": question},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exception:
            _record_external_error("orchestrator", "ask_question", "http_status", start)
            raise EvaluatorClientError(
                message=f"Erreur HTTP {exception.response.status_code} lors de l'appel à l'orchestrator",
                details={
                    "url": rag_orchestrator_url,
                    "response": exception.response.text,
                },
            ) from exception
        except httpx.ConnectError as exception:
            _record_external_error(
                "orchestrator", "ask_question", "connect_error", start
            )
            raise EvaluatorClientError(
                message="Impossible de se connecter à l'orchestrator",
                details={"url": rag_orchestrator_url, "error": str(exception)},
            ) from exception
        except httpx.TimeoutException as exception:
            _record_external_error("orchestrator", "ask_question", "timeout", start)
            raise EvaluatorClientError(
                message="Timeout lors de l'appel à l'orchestrator",
                details={"url": rag_orchestrator_url, "error": str(exception)},
            ) from exception
        except httpx.RequestError as exception:
            _record_external_error(
                "orchestrator", "ask_question", "request_error", start
            )
            raise EvaluatorClientError(
                message="Erreur réseau lors de l'appel à l'orchestrator",
                details={"url": rag_orchestrator_url, "error": str(exception)},
            ) from exception
        except ValueError as exception:
            _record_external_error(
                "orchestrator", "ask_question", "invalid_json", start
            )
            raise EvaluatorClientError(
                message="L'orchestrator a retourné une réponse JSON invalide",
                details={"url": rag_orchestrator_url},
            ) from exception

    evaluator_external_call_duration_seconds.labels(
        dependency="orchestrator", operation="ask_question", status="success"
    ).observe(time.perf_counter() - start)

    if not isinstance(data, dict):
        raise EvaluatorClientError(
            message="L'orchestrator a retourné un format inattendu",
            details={"url": rag_orchestrator_url, "response": data},
        )

    return data


def _record_external_error(
    dependency: str, operation: str, error_type: str, start: float
) -> None:
    """Enregistre une erreur d'appel externe evaluator.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        error_type: Type d'erreur à faible cardinalité.
        start: Instant de départ capturé avec `perf_counter` pour calculer une durée fiable.

    Returns:
        Aucune valeur.
    """
    evaluator_errors_total.labels(operation=operation, error_type=error_type).inc()
    evaluator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="error"
    ).observe(time.perf_counter() - start)
