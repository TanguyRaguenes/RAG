import json

import pytest

import rag_client
from config import McpConfig


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

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

    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
        return FakeResponse({"retrieved_chunks": [{"document": "doc"}]})


@pytest.mark.asyncio
async def test_retrieve_documentation_chunks_posts_question_with_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(rag_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await rag_client.retrieve_documentation_chunks(
        config=McpConfig("http://rag/retrieve_chunks", "http://oidc", "client", "secret"),
        question="Comment deployer ?",
        access_token="token",
    )

    assert json.loads(result) == [{"document": "doc"}]
    assert FakeAsyncClient.calls == [
        {
            "url": "http://rag/retrieve_chunks",
            "json": {"question": "Comment deployer ?"},
            "headers": {"Authorization": "Bearer token"},
            "timeout": 120,
        }
    ]
