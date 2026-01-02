import time

from fastapi import APIRouter, Depends
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.api.dependencies import get_config

from app.services.evaluating_service import evaluate_rag

router = APIRouter()

@router.post("/evaluate_rag", response_model=EvaluatorResponseBase)
async def ask_question_route(
        config = Depends(get_config),
    ) -> EvaluatorResponseBase:

    start = time.perf_counter()

    result = await evaluate_rag(config=config)

    elapsed = time.perf_counter() - start
    minutes, seconds = divmod(int(elapsed), 60)
    duration = f"{minutes:02d}:{seconds:02d}"
    
    return EvaluatorResponseBase(
        average_retrieval=result.average_retrieval,
        average_quality=result.average_quality,
        total_duration=duration,
        total_questions=result.total_questions,
    )
