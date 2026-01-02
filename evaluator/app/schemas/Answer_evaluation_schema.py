from pydantic import BaseModel

# Évaluation de la qualité de la réponse par le LLM Juge
class AnswerEvaluationBase(BaseModel):
    # Feedback concis sur la qualité
    feedback: str
    # Exactitude factuelle (1-5)
    accuracy: float
    # Exhaustivité (1-5)
    completeness: float
    # Pertinence (1-5)
    relevance: float