import logging

import pytest
from app import server
from app.core.errors import McpResponseContractError, McpTimeoutError
from mcp.server.auth.provider import AccessToken


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
    calls = []

    class FakeDocumentationService:
        async def answer(self, question: str, access_token: str) -> str:
            calls.append((question, access_token))
            return "chunks"

    monkeypatch.setattr(server, "get_access_token", _access_token)
    monkeypatch.setattr(server, "documentation_service", FakeDocumentationService())

    result = await server.interroger_documentation_interne("question")

    assert result.is_error is False
    assert result.content[0].text == "chunks"
    assert result.structured_content == {"result": "chunks"}
    assert calls == [("question", "user-token")]


@pytest.mark.asyncio
async def test_interroger_documentation_interne_requires_user_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "get_access_token", lambda: None)

    result = await server.interroger_documentation_interne("question")

    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "authentication_error"
    assert result.content[0].text == "L'authentification MCP est requise."


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected_level"),
    [
        (McpTimeoutError(), logging.WARNING),
        (McpResponseContractError(), logging.ERROR),
    ],
)
async def test_interroger_documentation_interne_returns_structured_client_errors(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected_level: int,
) -> None:
    class FailingDocumentationService:
        async def answer(self, question: str, access_token: str) -> str:
            raise error

    monkeypatch.setattr(server, "get_access_token", _access_token)
    monkeypatch.setattr(server, "documentation_service", FailingDocumentationService())

    with caplog.at_level(logging.DEBUG, logger=server.__name__):
        result = await server.interroger_documentation_interne("private question")

    assert result.is_error is True
    assert result.structured_content["error"]["code"] == error.code
    assert result.structured_content["error"]["retryable"] is error.retryable
    assert caplog.records[-1].levelno == expected_level
    assert caplog.records[-1].exc_info is None
    assert "private question" not in caplog.text


@pytest.mark.asyncio
async def test_interroger_documentation_interne_sanitizes_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingDocumentationService:
        async def answer(self, question: str, access_token: str) -> str:
            raise RuntimeError("private backend body")

    monkeypatch.setattr(server, "get_access_token", _access_token)
    monkeypatch.setattr(server, "documentation_service", FailingDocumentationService())

    result = await server.interroger_documentation_interne("private question")

    assert result.is_error is True
    assert result.structured_content["error"]["code"] == "mcp_error"
    assert "private backend body" not in result.content[0].text
