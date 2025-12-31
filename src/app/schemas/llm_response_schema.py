
from pydantic import BaseModel

from src.app.domain.models.ask_question_response_model import AskQuestionResponseModel

class LlmResponseBase(BaseModel):
    answer: AskQuestionResponseModel
    duration: str