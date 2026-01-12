
from pydantic import BaseModel

from app.domain.models.ask_question_response_model import AskQuestionResponseBase

class LlmResponseBase(BaseModel):
    answer: AskQuestionResponseBase
    duration: str