from typing import Literal

from pydantic import BaseModel


class RetrieveChunksRequestBase(BaseModel):
    question: str
    collection_profile: Literal["default", "evaluation"] = "default"
