from pydantic import BaseModel

class RetrievalEvaluationBase(BaseModel):

    mrr: float
    ndcg: float 
    recall:float
    precision:float
