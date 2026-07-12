import time

from opentelemetry import trace
from fastapi import APIRouter, Depends

from app.api.dependencies import get_config
from app.core.metrics import (
    SERVICE_NAME,
    evaluator_duration_seconds,
    evaluator_errors_total,
    evaluator_requests_total,
    rag_errors_total,
    rag_request_duration_seconds,
    rag_requests_total,
)
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.services.evaluating_service import evaluate_rag

router = APIRouter()
tracer = trace.get_tracer(__name__)


@router.post("/evaluate_rag", response_model=EvaluatorResponseBase)
async def ask_question_route(
    config=Depends(get_config),
) -> EvaluatorResponseBase:
    """Lance une évaluation complète du RAG sur le dataset configuré.

    Args:
        config: Configuration applicative chargée au démarrage.

    Returns:
        Scores moyens de retrieval, qualité de réponse, durée et volume de questions.

    Raises:
        EvaluatorContainerCustomException: Si le dataset, l'orchestrator ou le juge LLM échoue.
    """

    start = time.perf_counter()
    operation = "evaluate_rag"

    with tracer.start_as_current_span("evaluator.evaluate_rag_route"):
        try:
            result = await evaluate_rag(config=config)
        except Exception as exception:
            elapsed = time.perf_counter() - start
            evaluator_requests_total.labels(operation=operation, status="error").inc()
            evaluator_errors_total.labels(
                operation=operation, error_type=type(exception).__name__
            ).inc()
            evaluator_duration_seconds.labels(
                operation=operation, status="error"
            ).observe(elapsed)
            rag_requests_total.labels(
                service=SERVICE_NAME, operation=operation, status="error"
            ).inc()
            rag_errors_total.labels(
                service=SERVICE_NAME,
                operation=operation,
                error_type=type(exception).__name__,
            ).inc()
            rag_request_duration_seconds.labels(
                service=SERVICE_NAME, operation=operation, status="error"
            ).observe(elapsed)
            raise

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"

    evaluator_requests_total.labels(operation=operation, status="success").inc()
    evaluator_duration_seconds.labels(operation=operation, status="success").observe(
        elapsed
    )
    rag_requests_total.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).inc()
    rag_request_duration_seconds.labels(
        service=SERVICE_NAME, operation=operation, status="success"
    ).observe(elapsed)

    return EvaluatorResponseBase(
        average_retrieval=result.average_retrieval,
        average_answer_quality=result.average_answer_quality,
        total_duration=duration,
        total_questions=result.total_questions,
    )
