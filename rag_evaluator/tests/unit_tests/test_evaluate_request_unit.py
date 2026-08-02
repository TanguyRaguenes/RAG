import pytest
from pydantic import ValidationError

from app.schemas.evaluate_request_schema import EvaluateRequest


@pytest.mark.parametrize("question_limit", [1, 25, 50])
def test_evaluate_request_accepts_supported_limits(question_limit: int) -> None:
    request = EvaluateRequest(question_limit=question_limit)

    assert request.question_limit == question_limit


@pytest.mark.parametrize("question_limit", [0, 51, True, "10"])
def test_evaluate_request_rejects_invalid_limits(question_limit: object) -> None:
    with pytest.raises(ValidationError):
        EvaluateRequest(question_limit=question_limit)
