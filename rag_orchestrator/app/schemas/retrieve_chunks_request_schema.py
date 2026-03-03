from pydantic import BaseModel


class RetrieveChunksRequestBase(BaseModel):
    question: str
