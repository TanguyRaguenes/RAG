from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class JudgeOutput(BaseModel):
    feedback: str = Field(description="Short evaluator feedback")
    accuracy: int = Field(ge=1, le=5)
    completeness: int = Field(ge=1, le=5)
    relevance: int = Field(ge=1, le=5)

judge_parser = PydanticOutputParser(pydantic_object=JudgeOutput)