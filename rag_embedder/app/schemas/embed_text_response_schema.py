from pydantic import BaseModel

class EmbedTextResponseBase(BaseModel):
    embeded_text: list[float]
