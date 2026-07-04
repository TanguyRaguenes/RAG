from typing import Literal

from pydantic import BaseModel


class AskQuestionRequestBase(BaseModel):
    question: str
    provider: Literal["local", "api"]
    channel: Literal["streamlit", "mcp", "api"] = "api"
