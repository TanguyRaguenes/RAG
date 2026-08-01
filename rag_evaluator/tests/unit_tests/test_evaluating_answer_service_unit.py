import pytest
from app.core.config import EvaluatorConfig
from app.core.exceptions import JudgeEvaluationException
from app.schemas.judge_schema import JudgeMessage
from app.services import evaluating_answer_service as service


def _config() -> EvaluatorConfig:
    return EvaluatorConfig.model_validate(
        {
            "llm": {
                "provider": "ollama",
                "url_provider": "http://ollama",
                "model": "judge",
                "temperature": 0.1,
                "num_ctx": 1024,
                "max_output_token": 128,
                "timeout_seconds": 10,
            },
            "evaluation_method": {"use_api_openai": False},
        }
    )


class FakeJudgeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.messages: list[JudgeMessage] = []

    async def judge(self, messages: list[JudgeMessage]) -> str:
        self.messages = messages
        return self.response


@pytest.mark.asyncio
async def test_evaluate_answer_uses_injected_judge_client() -> None:
    judge = FakeJudgeClient(
        '{"feedback":"ok","accuracy":4,"completeness":3,'
        '"relevance":5,"faithfulness":4,"safe_refusal":5}'
    )

    result = await service.evaluate_answer(
        _config(),
        "question",
        "generated",
        "reference",
        [],
        expected_answer_points=["point attendu"],
        expected_behavior="answer",
        judge_client=judge,
    )

    assert result.accuracy == 4
    assert result.faithfulness == 4
    assert judge.messages[0].role == "system"


@pytest.mark.asyncio
async def test_evaluate_answer_rejects_invalid_judgement() -> None:
    with pytest.raises(JudgeEvaluationException):
        await service.evaluate_answer(
            _config(),
            "question",
            "generated",
            "reference",
            [],
            judge_client=FakeJudgeClient("not-json"),
        )


@pytest.mark.asyncio
async def test_evaluate_answer_does_not_mask_unexpected_parser_bug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_unexpectedly(_parser: object, _value: str) -> None:
        raise RuntimeError("programming bug")

    monkeypatch.setattr(type(service.judge_parser), "parse", fail_unexpectedly)

    with pytest.raises(RuntimeError, match="programming bug"):
        await service.evaluate_answer(
            _config(),
            "question",
            "generated",
            "reference",
            [],
            judge_client=FakeJudgeClient("valid-looking"),
        )
