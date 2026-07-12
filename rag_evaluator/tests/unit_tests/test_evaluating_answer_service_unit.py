import pytest

from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.services import evaluating_answer_service as service


class FakeJudgeOutput:
    def model_dump(self) -> dict:
        return {"feedback": "ok", "accuracy": 4, "completeness": 3, "relevance": 5}


class FakeParser:
    def parse(self, raw: str) -> FakeJudgeOutput:
        assert raw == "raw-json"
        return FakeJudgeOutput()


@pytest.mark.asyncio
async def test_evaluate_answer_uses_local_judge_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def fake_build_judge_messages(**kwargs):
        calls.append(("messages", kwargs))
        return [{"role": "user", "content": "judge"}]

    async def fake_judge_client(config, messages):
        calls.append(("local", config, messages))
        return {"llm_answer": "raw-json"}

    monkeypatch.setattr(service, "build_judge_messages", fake_build_judge_messages)
    monkeypatch.setattr(service, "judge_client", fake_judge_client)
    monkeypatch.setattr(service, "judge_parser", FakeParser())

    result = await service.evaluate_answer(
        {"evaluation_method": {"use_api_openai": False}},
        "question",
        "generated",
        "reference",
        [],
    )

    assert isinstance(result, AnswerEvaluationBase)
    assert result.accuracy == 4
    assert calls[1] == (
        "local",
        {"evaluation_method": {"use_api_openai": False}},
        [{"role": "user", "content": "judge"}],
    )


@pytest.mark.asyncio
async def test_evaluate_answer_uses_openai_judge_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_judge_client_api_openia(payload, timeout, base_url, api_key):
        calls.append((payload, timeout, base_url, api_key))
        return {"llm_answer": "raw-json"}

    monkeypatch.setenv("OPEN_API_KEY", "api-key")
    monkeypatch.setattr(
        service,
        "build_judge_messages",
        lambda **kwargs: [{"role": "user", "content": "judge"}],
    )
    monkeypatch.setattr(
        service, "judge_client_api_openia", fake_judge_client_api_openia
    )
    monkeypatch.setattr(service, "judge_parser", FakeParser())

    result = await service.evaluate_answer(
        {
            "evaluation_method": {"use_api_openai": True},
            "llm": {"timeout_seconds": 12, "temperature": 0.1, "max_output_token": 128},
        },
        "question",
        "generated",
        "reference",
        [],
    )

    assert result.relevance == 5
    assert calls[0][0]["model"] == "gpt-4o"
    assert calls[0][1:] == (12, "https://api.openai.com/v1/chat/completions", "api-key")
