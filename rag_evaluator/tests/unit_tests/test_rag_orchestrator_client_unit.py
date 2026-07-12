import httpx
import pytest

from app.core.exceptions import EvaluatorClientError
from app.dal.client import rag_orchestrator_client as client


class FakeResponse:
    def __init__(self, payload, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "http://orchestrator/ask_question")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []
    response = FakeResponse({"llm_response": "ok"})

    def __init__(self, timeout: float):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return self.response


@pytest.mark.asyncio
async def test_ask_question_posts_question_to_configured_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"llm_response": "ok"})
    monkeypatch.setenv(
        "RAG_ORCHESTRATOR_ASK_QUESTION_URL", "http://orchestrator/ask_question"
    )
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    result = await client.ask_question("Question")

    assert result == {"llm_response": "ok"}
    assert FakeAsyncClient.calls == [
        {
            "url": "http://orchestrator/ask_question",
            "json": {"question": "Question"},
            "timeout": 180.0,
        }
    ]


@pytest.mark.asyncio
async def test_ask_question_raises_client_error_when_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL", raising=False)

    with pytest.raises(EvaluatorClientError) as exc_info:
        await client.ask_question("Question")

    assert exc_info.value.details == {"env_var": "RAG_ORCHESTRATOR_ASK_QUESTION_URL"}


@pytest.mark.asyncio
async def test_ask_question_rejects_non_dict_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse(["invalid"])
    monkeypatch.setenv(
        "RAG_ORCHESTRATOR_ASK_QUESTION_URL", "http://orchestrator/ask_question"
    )
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorClientError, match="format inattendu"):
        await client.ask_question("Question")
