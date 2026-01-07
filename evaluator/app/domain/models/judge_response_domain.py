from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class JudgeOutput(BaseModel):
    feedback: str = Field(
        description="Concise feedback on the answer quality, comparing it to the reference answer and evaluating based on the retrieved context"
    )
    accuracy: int = Field(
        ge=1, # Greater than or Equal to
        le=5, # Less than or Equal to
        description="How factually correct is the answer compared to the reference answer? 1 (wrong. any wrong answer must score 1) to 5 (ideal - perfectly accurate). An acceptable answer would score 3.")
    
    completeness: int = Field(
        ge=1, 
        le=5, 
        description="How complete is the answer in addressing all aspects of the question? 1 (very poor - missing key information) to 5 (ideal - all the information from the reference answer is provided completely). Only answer 5 if ALL information from the reference answer is included."
    )
    relevance: int = Field(
        ge=1, 
        le=5,
        description="How relevant is the answer to the specific question asked? 1 (very poor - off-topic) to 5 (ideal - directly addresses question and gives no additional information). Only answer 5 if the answer is completely relevant to the question and gives no additional information."
        )

judge_parser = PydanticOutputParser(pydantic_object=JudgeOutput)