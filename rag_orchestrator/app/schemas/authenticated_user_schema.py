from pydantic import BaseModel, Field


class AuthenticatedUser(BaseModel):
    sub: str
    email: str | None = None
    name: str | None = None
    preferred_username: str | None = None
    groups: list[str] = Field(default_factory=list)
