from pydantic import BaseModel

class embeddingRequestBase(BaseModel):
    text_to_embed: str