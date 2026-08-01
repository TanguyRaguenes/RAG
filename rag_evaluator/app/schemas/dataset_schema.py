from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel

NonEmptyString = Annotated[str, Field(min_length=1)]


class EvaluationCase(BaseModel):
    """Cas d'évaluation intégralement validé avant le premier appel externe."""

    question: NonEmptyString
    reference_answer: NonEmptyString
    keywords: list[NonEmptyString] = Field(default_factory=list)
    expected_sources: list[NonEmptyString] | None = None
    expected_answer_points: list[NonEmptyString] | None = None
    expected_behavior: Literal["answer", "refuse"] = "answer"
    category: str | None = None


class EvaluationDataset(RootModel[list[EvaluationCase]]):
    """Dataset d'évaluation validé comme une collection de cas cohérents."""
