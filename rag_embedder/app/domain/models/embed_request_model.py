from pydantic import BaseModel, Field


class EmbedRequestBase(BaseModel):
    texts: list[str] = Field(min_length=1)
