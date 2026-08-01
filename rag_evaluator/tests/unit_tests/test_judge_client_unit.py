from typing import ClassVar, Self

import httpx
import pytest

from app.core.config import EvaluatorConfig
from app.core.exceptions import EvaluatorClientError
from app.dal.clients import judge_client as client
from app.dal.clients.judge_client import LocalJudgeClient, OpenAIJudgeClient
from app.schemas.judge_schema import JudgeMessage


def _config(*, use_openai: bool = False) -> EvaluatorConfig:
    return EvaluatorConfig.model_validate(
        {
            "llm": {
                "provider": "ollama",
                "url_provider": "http://ollama:11434",
                "model": "judge-model",
                "stream": False,
                "temperature": 0.1,
                "num_ctx": 4096,
                "max_output_token": 512,
                "timeout_seconds": 10,
            },
            "evaluation_method": {"use_api_openai": use_openai},
        }
    )


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
async def test_openai_client_respects_chat_completions_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    result = await OpenAIJudgeClient(_config(use_openai=True), "secret").judge(
        [JudgeMessage(role="user", content="judge")]
    )

    assert result == "judgement"
    assert FakeAsyncClient.calls == [
        {
            "url": "https://api.openai.com/v1/chat/completions",
            "json": {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "judge"}],
                "temperature": 0.1,
                "max_completion_tokens": 512,
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
    config = _config(use_openai=True)
    config.evaluation_method.openai_url = (
        "https://openai-proxy.example/v1/chat/completions"
    )
    config.evaluation_method.openai_model = "gpt-5-mini"
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    await OpenAIJudgeClient(config, "secret").judge(
        [JudgeMessage(role="user", content="judge")]
    )

    assert FakeAsyncClient.calls[0]["url"] == (
        "https://openai-proxy.example/v1/chat/completions"
    )
    assert FakeAsyncClient.calls[0]["json"]["model"] == "gpt-5-mini"


@pytest.mark.asyncio
async def test_local_client_uses_openai_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
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
