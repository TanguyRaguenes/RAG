from pydantic import BaseModel

class IngestRequestBase(BaseModel):
    text_to_embed: str