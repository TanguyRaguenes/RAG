from pydantic import BaseModel

class EmbedTextRequestBase(BaseModel):
    text: str