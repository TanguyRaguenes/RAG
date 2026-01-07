from pydantic import BaseModel
from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase

class EvaluatorResponseBase(BaseModel):
    average_retrieval: RetrievalEvaluationBase
    average_answer_quality: AnswerEvaluationBase
    total_duration: str
    total_questions: int