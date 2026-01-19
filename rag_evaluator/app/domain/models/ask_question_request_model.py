
from pydantic import BaseModel

class AskQuestionRequestBase(BaseModel):
    question: str