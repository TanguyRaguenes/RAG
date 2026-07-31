import json
from typing import ClassVar

import pytest
import rag_client
from config import McpConfig


def _config() -> McpConfig:
    return McpConfig(
        rag_orchestrator_url="http://rag/retrieve_chunks",
        oidc_issuer="https://auth.example.test",
        oidc_jwks_uri="https://auth.example.test/jwks.json",
        oidc_allowed_audiences=["https://mcp.example.test/"],
        required_scopes=["rag:mcp"],
        resource_server_url="https://mcp.example.test",
    )


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict]] = []

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict, headers: dict) -> FakeResponse:
        self.calls.append(
            {"url": url, "json": json, "headers": headers, "timeout": self.timeout}
        )
        return FakeResponse({"retrieved_chunks": [{"document": "doc"}]})


@pytest.mark.asyncio
async def test_retrieve_documentation_chunks_posts_question_with_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(rag_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await rag_client.retrieve_documentation_chunks(
        config=_config(),
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
