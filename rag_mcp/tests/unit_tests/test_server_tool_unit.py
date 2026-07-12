import httpx
import pytest

import server
from config import McpConfig


@pytest.mark.asyncio
async def test_interroger_documentation_interne_returns_rag_client_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = McpConfig("http://rag", "http://oidc", "client", "secret")
    calls = []

    async def fake_get_access_token(received_config: McpConfig) -> str:
        calls.append(("token", received_config))
        return "access-token"

    async def fake_retrieve_documentation_chunks(**kwargs) -> str:
        calls.append(("rag", kwargs))
        return "chunks"

    monkeypatch.setattr(server, "load_mcp_config", lambda: config)
    monkeypatch.setattr(server, "get_access_token", fake_get_access_token)
    monkeypatch.setattr(
        server, "retrieve_documentation_chunks", fake_retrieve_documentation_chunks
    )

    result = await server.interroger_documentation_interne("question")

    assert result == "chunks"
    assert calls == [
        ("token", config),
        (
            "rag",
            {"config": config, "question": "question", "access_token": "access-token"},
        ),
    ]


@pytest.mark.asyncio
async def test_interroger_documentation_interne_formats_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get_access_token(config: McpConfig) -> str:
        return "token"

    async def failing_retrieve_documentation_chunks(**kwargs) -> str:
        request = httpx.Request("POST", "http://rag")
        response = httpx.Response(503, text="down", request=request)
        raise httpx.HTTPStatusError("failed", request=request, response=response)

    monkeypatch.setattr(
        server,
        "load_mcp_config",
        lambda: McpConfig("http://rag", "http://oidc", "client", "secret"),
    )
    monkeypatch.setattr(server, "get_access_token", fake_get_access_token)
    monkeypatch.setattr(
        server, "retrieve_documentation_chunks", failing_retrieve_documentation_chunks
    )

    result = await server.interroger_documentation_interne("question")

    assert result == "Erreur HTTP lors de l'appel au RAG : 503 - down"
