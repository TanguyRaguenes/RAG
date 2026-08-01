import math

from pydantic import BaseModel, Field, RootModel, StrictInt, field_validator


class RerankingProviderResult(BaseModel):
    """Score externe associé exactement à un index de chunk."""

    index: StrictInt
    score: float = Field(ge=0.0, le=1.0)

    @field_validator("score", mode="before")
    @classmethod
    def validate_score(cls, value: object) -> object:
        """Refuse les booléens, valeurs non numériques et nombres non finis.

        Args:
            value: Score brut retourné par le fournisseur.

        Returns:
            Valeur numérique qui sera ensuite bornée par Pydantic.

        Raises:
            ValueError: Si le score est booléen ou non fini.
            TypeError: Si le score n'est pas numérique.
        """
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError("score must be a real number")
        if not math.isfinite(float(value)):
            raise ValueError("score must be finite")
        return value


class RerankingProviderResponse(RootModel[list[RerankingProviderResult]]):
    """Liste de scores retournée par le fournisseur de reranking."""
