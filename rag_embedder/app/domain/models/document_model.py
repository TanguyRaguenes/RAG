from pydantic import BaseModel

class DocumentBase(BaseModel):
    path: str
    content: str

class DocumentsBase(BaseModel):
    documents: list[DocumentBase]