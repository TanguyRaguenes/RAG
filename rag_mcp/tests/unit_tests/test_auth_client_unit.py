import pytest

import auth_client
from config import McpConfig


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, data: dict, headers: dict) -> FakeResponse:
        self.calls.append(
            {"url": url, "data": data, "headers": headers, "timeout": self.timeout}
        )
        return FakeResponse({"access_token": "new-token", "expires_in": 120})


@pytest.mark.asyncio
async def test_get_access_token_returns_cached_token_when_it_is_still_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_client._token_cache.clear()
    auth_client._token_cache.update({"access_token": "cached", "expires_at": 200})
    monkeypatch.setattr(auth_client.time, "time", lambda: 100)

    token = await auth_client.get_access_token(
        McpConfig("http://rag", "http://oidc", "client", "secret")
    )

    assert token == "cached"


@pytest.mark.asyncio
async def test_get_access_token_requests_oidc_and_updates_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_client._token_cache.clear()
    FakeAsyncClient.calls = []
    monkeypatch.setattr(auth_client.time, "time", lambda: 100)
    monkeypatch.setattr(auth_client.httpx, "AsyncClient", FakeAsyncClient)

    token = await auth_client.get_access_token(
        McpConfig("http://rag", "http://oidc/token", "client-id", "secret")
    )

    assert token == "new-token"
    assert auth_client._token_cache == {"access_token": "new-token", "expires_at": 220}
    assert FakeAsyncClient.calls == [
        {
            "url": "http://oidc/token",
            "data": {
                "grant_type": "client_credentials",
                "client_id": "client-id",
                "client_secret": "secret",
            },
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "timeout": 20,
        }
    ]
