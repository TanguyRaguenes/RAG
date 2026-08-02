from pydantic import BaseModel, ConfigDict, Field


# Évaluation de la qualité de la réponse par le LLM Juge
class AnswerEvaluationBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Feedback concis sur la qualité
    feedback: str = Field(min_length=1)
    # Exactitude factuelle (1-5)
    accuracy: float = Field(ge=0, le=5)
    # Exhaustivité (1-5)
    completeness: float = Field(ge=0, le=5)
    # Pertinence (1-5)
    relevance: float = Field(ge=0, le=5)
    # Fidélité aux sources récupérées (1-5)
    faithfulness: float = Field(ge=0, le=5)
    # Qualité du refus lorsque la question ne doit pas recevoir de réponse factuelle (1-5)
    safe_refusal: float = Field(ge=0, le=5)
