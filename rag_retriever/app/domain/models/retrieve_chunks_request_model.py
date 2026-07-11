from pydantic import BaseModel


class RetrieveChunksRequestBase(BaseModel):
    embeded_question: list[float]


class RetrieveDocumentChunksRequestBase(BaseModel):
    paths: list[str]
