from datetime import datetime

from pydantic import BaseModel, Field


class QuotaUsageResponse(BaseModel):
    utilisateur_id: str
    email: str | None = None
    display_name: str | None = None
    preferred_username: str | None = None
    max_tokens_par_mois: int
    consumed_tokens: int
    remaining_tokens: int
    usage_ratio: float
    actif: bool
    date_debut: datetime
    date_fin: datetime | None = None


class UpdateQuotaRequest(BaseModel):
    max_tokens_par_mois: int = Field(gt=0)
    actif: bool
