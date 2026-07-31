from pydantic import BaseModel


class RetrievalEvaluationBase(BaseModel):
    mrr: float
    ndcg: float
    recall: float
    precision: float
    source_hit_at_5: float = 0
