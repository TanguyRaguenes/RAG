import pytest

from app.core.config import EvaluatorConfig
from app.core.exceptions import JudgeEvaluationException
from app.schemas.judge_schema import JudgeMessage
from app.services import evaluating_answer_service as service


def _config() -> EvaluatorConfig:
    return EvaluatorConfig.model_validate(
        {
            "rag_provider": "api",
            "judge_provider": "local",
            "llm": {
                "common": {
                    "temperature": 0.1,
                    "timeout_seconds": 10,
                    "stream": False,
                },
                "local": {
                    "provider": "Ollama",
                    "endpoint": "http://ollama/v1/chat/completions",
                    "model": "judge",
                    "context_window_tokens": 1024,
                    "max_output_tokens": 128,
                    "max_prompt_chars": 2000,
                },
                "api": {
                    "provider": "OpenAi",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "model": "judge-api",
                    "max_output_tokens": 128,
                    "max_prompt_chars": 4000,
                },
            },
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
