from pydantic import BaseModel


class EmbedTextResponseBase(BaseModel):
    duration_ms: float
    duration_human: str
    embeded_texts: list[list[float]]
