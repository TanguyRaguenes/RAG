import httpx
import pytest
from mcp.server.auth.provider import AccessToken

import server
from config import McpConfig


def _config() -> McpConfig:
    return McpConfig(
        rag_orchestrator_url="http://rag",
        oidc_issuer="https://auth.example.test",
        oidc_jwks_uri="https://auth.example.test/jwks.json",
        oidc_allowed_audiences=["https://mcp.example.test/"],
        required_scopes=["rag:mcp"],
        resource_server_url="https://mcp.example.test",
    )


def _access_token(token: str = "user-token") -> AccessToken:
    return AccessToken(
        token=token,
        client_id="kilo-mcp-client",
        scopes=["rag:mcp"],
        subject="user-sub",
        claims={"sub": "user-sub"},
    )


@pytest.mark.asyncio
async def test_interroger_documentation_interne_returns_rag_client_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    calls = []

    async def fake_retrieve_documentation_chunks(**kwargs) -> str:
        calls.append(("rag", kwargs))
        return "chunks"

    monkeypatch.setattr(server, "config", config)
    monkeypatch.setattr(server, "get_access_token", _access_token)
    monkeypatch.setattr(
        server, "retrieve_documentation_chunks", fake_retrieve_documentation_chunks
    )

    result = await server.interroger_documentation_interne("question")

    assert result == "chunks"
    assert calls == [
        (
            "rag",
            {"config": config, "question": "question", "access_token": "user-token"},
        ),
    ]


@pytest.mark.asyncio
async def test_interroger_documentation_interne_requires_user_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "get_access_token", lambda: None)

    result = await server.interroger_documentation_interne("question")

    assert result == "Erreur MCP : Token utilisateur MCP manquant"


@pytest.mark.asyncio
async def test_interroger_documentation_interne_formats_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def failing_retrieve_documentation_chunks(**kwargs) -> str:
        request = httpx.Request("POST", "http://rag")
        response = httpx.Response(503, text="down", request=request)
        raise httpx.HTTPStatusError("failed", request=request, response=response)

    monkeypatch.setattr(server, "config", _config())
    monkeypatch.setattr(server, "get_access_token", _access_token)
    monkeypatch.setattr(
        server, "retrieve_documentation_chunks", failing_retrieve_documentation_chunks
    )

    result = await server.interroger_documentation_interne("question")

    assert result == "Erreur HTTP lors de l'appel au RAG : 503 - down"
