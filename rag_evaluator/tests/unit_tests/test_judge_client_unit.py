from typing import ClassVar, Self

import httpx
import pytest

from app.core.config import EvaluatorConfig
from app.core.exceptions import EvaluatorClientError
from app.dal.clients import judge_client as client
from app.dal.clients.judge_client import LocalJudgeClient, OpenAIJudgeClient
from app.domain.models.judge_response_model import JudgeOutput
from app.schemas.judge_schema import JudgeMessage


def _config(*, judge_provider: str = "local") -> EvaluatorConfig:
    return EvaluatorConfig.model_validate(
        {
            "rag_provider": "api",
            "judge_provider": judge_provider,
            "llm": {
                "common": {
                    "stream": False,
                    "temperature": 0.1,
                    "timeout_seconds": 10,
                },
                "local": {
                    "provider": "Ollama",
                    "endpoint": "http://ollama:11434/v1/chat/completions",
                    "model": "judge-local",
                    "context_window_tokens": 4096,
                    "max_output_tokens": 512,
                    "max_prompt_chars": 8000,
                },
                "api": {
                    "provider": "OpenAi",
                    "endpoint": "https://api.openai.com/v1/responses",
                    "model": "judge-api",
                    "max_output_tokens": 512,
                    "max_prompt_chars": 12000,
                },
            },
        }
    )


def test_judge_output_json_schema_is_strict_and_bounded() -> None:
    schema = JudgeOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "feedback",
        "accuracy",
        "completeness",
        "relevance",
        "faithfulness",
        "safe_refusal",
    }
    assert schema["properties"]["accuracy"]["minimum"] == 1
    assert schema["properties"]["accuracy"]["maximum"] == 5


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://judge")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self) -> object:
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict[str, object]]] = []
    response: ClassVar[FakeResponse] = FakeResponse(
        {"choices": [{"message": {"content": "judgement"}}]}
    )

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def post(
        self,
        url: str,
        json: dict[str, object],
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": self.timeout}
        )
        return self.response


@pytest.mark.asyncio
async def test_openai_client_respects_responses_api_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse(
        {
            "output": [
                {"type": "reasoning"},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "judgement"}],
                },
            ]
        }
    )
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    result = await OpenAIJudgeClient(_config(judge_provider="api"), "secret").judge(
        [JudgeMessage(role="user", content="judge")]
    )

    assert result == "judgement"
    assert FakeAsyncClient.calls == [
        {
            "url": "https://api.openai.com/v1/responses",
            "json": {
                "model": "judge-api",
                "input": [{"role": "user", "content": "judge"}],
                "stream": False,
                "max_output_tokens": 512,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "rag_judge_evaluation",
                        "strict": True,
                        "schema": JudgeOutput.model_json_schema(),
                    }
                },
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer secret",
            },
            "timeout": 10.0,
        }
    ]


@pytest.mark.asyncio
async def test_openai_client_uses_configured_url_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    config = _config(judge_provider="api")
    config.llm.api.endpoint = "https://openai-proxy.example/v1/responses"
    config.llm.api.model = "gpt-5-mini"
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    await OpenAIJudgeClient(config, "secret").judge(
        [JudgeMessage(role="user", content="judge")]
    )

    assert FakeAsyncClient.calls[0]["url"] == (
        "https://openai-proxy.example/v1/responses"
    )
    assert FakeAsyncClient.calls[0]["json"]["model"] == "gpt-5-mini"


@pytest.mark.asyncio
async def test_local_client_uses_openai_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse(
        {"choices": [{"message": {"content": "judgement"}}]}
    )
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    await LocalJudgeClient(_config()).judge(
        [JudgeMessage(role="system", content="judge")]
    )

    assert FakeAsyncClient.calls[0]["url"] == (
        "http://ollama:11434/v1/chat/completions"
    )
    assert FakeAsyncClient.calls[0]["json"]["max_tokens"] == 512
    assert "options" not in FakeAsyncClient.calls[0]["json"]


@pytest.mark.asyncio
async def test_judge_client_rejects_missing_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({"choices": []})
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorClientError, match="Réponse du juge LLM invalide"):
        await LocalJudgeClient(_config()).judge(
            [JudgeMessage(role="user", content="judge")]
        )

    FakeAsyncClient.response = FakeResponse(
        {"choices": [{"message": {"content": "judgement"}}]}
    )


@pytest.mark.asyncio
async def test_judge_client_wraps_http_status_without_response_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({"secret": "upstream"}, status_code=500)
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorClientError) as exc_info:
        await LocalJudgeClient(_config()).judge(
            [JudgeMessage(role="user", content="judge")]
        )

    assert exc_info.value.details == {"status_code": 500}
    FakeAsyncClient.response = FakeResponse(
        {"choices": [{"message": {"content": "judgement"}}]}
    )
