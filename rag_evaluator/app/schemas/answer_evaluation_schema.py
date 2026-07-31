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
    # Fidélité aux sources récupérées (1-5)
    faithfulness: float = 0
    # Qualité du refus lorsque la question ne doit pas recevoir de réponse factuelle (1-5)
    safe_refusal: float = 0
