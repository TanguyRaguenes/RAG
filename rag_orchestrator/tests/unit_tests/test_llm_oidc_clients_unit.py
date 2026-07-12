import httpx
import pytest

from app.core.exceptions import LlmApiException
from app.dal.clients import llm_client, oidc_client


class FakeResponse:
    def __init__(self, payload, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "http://llm")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []
    response = FakeResponse({"ok": True})

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict, headers=None) -> FakeResponse:
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": self.timeout,
            }
        )
        return self.response

    async def get(self, url: str, headers=None) -> FakeResponse:
        self.calls.append(
            {"method": "GET", "url": url, "headers": headers, "timeout": self.timeout}
        )
        return self.response


@pytest.mark.asyncio
async def test_ask_question_to_llm_posts_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"choices": []})
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.ask_question_to_llm({"model": "m"}, 12, "http://llm")

    assert result == {"choices": []}
    assert FakeAsyncClient.calls == [
        {
            "method": "POST",
            "url": "http://llm",
            "json": {"model": "m"},
            "headers": None,
            "timeout": 12,
        }
    ]


@pytest.mark.asyncio
async def test_ask_question_to_api_sends_bearer_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"output": []})
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.ask_question_to_api({"model": "m"}, "http://api", "key")

    assert result == {"output": []}
    assert FakeAsyncClient.calls[0]["headers"] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer key",
    }


@pytest.mark.asyncio
async def test_ask_question_to_llm_wraps_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({}, status_code=500, text="down")
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(LlmApiException, match="Erreur HTTP 500"):
        await llm_client.ask_question_to_llm({}, 12, "http://llm")


@pytest.mark.asyncio
async def test_oidc_get_userinfo_returns_empty_dict_without_url() -> None:
    client = oidc_client.OidcClient("issuer", "http://jwks", userinfo_url=None)

    assert await client.get_userinfo("token") == {}


@pytest.mark.asyncio
async def test_oidc_get_userinfo_calls_userinfo_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"email": "user@example.com"})
    monkeypatch.setattr(oidc_client.httpx, "AsyncClient", FakeAsyncClient)
    client = oidc_client.OidcClient(
        "issuer", "http://jwks", userinfo_url="http://userinfo"
    )

    assert await client.get_userinfo("token") == {"email": "user@example.com"}
    assert FakeAsyncClient.calls == [
        {
            "method": "GET",
            "url": "http://userinfo",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 10,
        }
    ]
