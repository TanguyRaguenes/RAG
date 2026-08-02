from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RetrievedChunk(BaseModel):
    """Chunk externe retourné par l'orchestrator."""

    model_config = ConfigDict(extra="allow")

    document: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float | None = None


class AskQuestionRequest(BaseModel):
    """Corps HTTP envoyé à l'orchestrator."""

    question: str = Field(min_length=1)
    provider: Literal["local", "api"]
    channel: Literal["api"] = "api"
    collection_profile: Literal["evaluation"] = "evaluation"


class AskQuestionResponse(BaseModel):
    """Réponse HTTP validée de l'orchestrator."""

    llm_response: str
    retrieved_chunks: list[RetrievedChunk]
    retrieved_documents: dict[str, int]
    model: str
    generated_prompt: list[dict[str, Any]]
    duration: str


class AuthenticatedUser(BaseModel):
    """Identité validée par l'endpoint `/auth/me` de l'orchestrator."""

    issuer: str
    sub: str
    email: str | None = None
    name: str | None = None
    display_name: str | None = None
    preferred_username: str | None = None
    groups: list[str] = Field(default_factory=list)
