import pytest

from app.core.exceptions import EvaluatorClientError
from app.dal.client.judge_client import (
    build_auth_headers,
    build_judge_payload,
    format_judge_response,
)


def test_build_judge_payload_maps_config_to_ollama_options() -> None:
    config = {
        "llm": {
            "model": "judge-model",
            "stream": False,
            "temperature": 0.1,
            "num_ctx": 4096,
            "max_output_token": 512,
        }
    }
    messages = [{"role": "user", "content": "Evaluer"}]

    payload = build_judge_payload(config, messages)

    assert payload == {
        "model": "judge-model",
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }


def test_build_auth_headers_adds_bearer_token_when_available() -> None:
    assert build_auth_headers("token") == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token",
    }


def test_build_auth_headers_without_token_keeps_content_type_only() -> None:
    assert build_auth_headers(None) == {"Content-Type": "application/json"}


def test_format_judge_response_extracts_llm_answer() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"accuracy": 5}',
                }
            }
        ]
    }

    assert format_judge_response(response) == {"llm_answer": '{"accuracy": 5}'}


def test_format_judge_response_rejects_invalid_payload() -> None:
    with pytest.raises(EvaluatorClientError):
        format_judge_response({"choices": []})
import httpx
import pytest

from app.core.exceptions import EvaluatorClientError
from app.dal.client import judge_client as client


class FakeResponse:
    def __init__(self, payload, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "http://judge")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []
    response = FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict, headers=None) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
        return self.response


@pytest.mark.asyncio
async def test_post_json_returns_dict_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"choices": []})
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    result = await client._post_json(url="http://judge", payload={"p": 1}, timeout_seconds=5, headers={"h": "v"})

    assert result == {"choices": []}
    assert FakeAsyncClient.calls == [{"url": "http://judge", "json": {"p": 1}, "headers": {"h": "v"}, "timeout": 5}]


@pytest.mark.asyncio
async def test_post_json_wraps_http_status_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.response = FakeResponse({}, status_code=500, text="ko")
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorClientError, match="Erreur HTTP 500"):
        await client._post_json(url="http://judge", payload={}, timeout_seconds=5)


@pytest.mark.asyncio
async def test_judge_client_builds_local_endpoint_and_formats_response(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"choices": [{"message": {"content": "answer"}}]})
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    result = await client.judge_client(
        {
            "llm": {
                "url_provider": "http://ollama",
                "timeout_seconds": 10,
                "model": "model",
                "stream": False,
                "temperature": 0,
                "num_ctx": 1024,
                "max_output_token": 128,
            }
        },
        [{"role": "user", "content": "judge"}],
    )

    assert result == {"llm_answer": "answer"}
    assert FakeAsyncClient.calls[0]["url"] == "http://ollama/v1/chat/completions"
