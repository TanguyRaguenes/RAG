from pydantic import BaseModel, Field

from app.schemas.answer_evaluation_schema import AverageAnswerEvaluationBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase


class EvaluatorResponseBase(BaseModel):
    average_retrieval: RetrievalEvaluationBase
    average_answer_quality: AverageAnswerEvaluationBase
    total_duration: str
    total_questions: int = Field(ge=0)
    successful_questions: int = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    average_latency_seconds: float = Field(ge=0)
    p95_latency_seconds: float = Field(ge=0)
    p99_latency_seconds: float = Field(ge=0)
