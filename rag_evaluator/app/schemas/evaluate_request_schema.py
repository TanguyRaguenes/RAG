from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """Paramètres optionnels pour limiter une évaluation manuelle."""

    question_limit: int | None = Field(default=None, ge=1, le=50, strict=True)
