from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    note: Literal[-1, 1]
    commentaire: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    interaction_id: int
    note: int
    commentaire: str | None = None


class AdminInteractionChunkResponse(BaseModel):
    rang: int
    score: float | None = None
    titre: str
    chemin: str
    contenu: str


class AdminInteractionFeedbackResponse(BaseModel):
    interaction_id: int
    cree_le: datetime
    question: str
    reponse: str | None = None
    note: int | None = None
    commentaire: str | None = None
    chunks: list[AdminInteractionChunkResponse] = Field(default_factory=list)
