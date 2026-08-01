import json

import pytest
from app.core.config import load_mcp_config
from app.core.errors import McpConfigError
from app.schemas.rag_response import RetrievedChunksResponse
from app.server import AUTH_SETTINGS, TRANSPORT_SECURITY
from app.services.documentation_service import DocumentationService


class FakeRagClient:
    def __init__(self, chunks: tuple[dict, ...]) -> None:
        self.chunks = chunks

    async def retrieve_documentation_chunks(
        self, question: str, access_token: str
    ) -> RetrievedChunksResponse:
        return RetrievedChunksResponse(self.chunks)


@pytest.mark.asyncio
async def test_documentation_service_returns_empty_message() -> None:
    result = await DocumentationService(FakeRagClient(())).answer("question", "token")

    assert result == "Aucune information trouvée."


@pytest.mark.asyncio
async def test_documentation_service_serializes_chunks() -> None:
    chunks = [{"document": "Résumé", "metadata": {"title": "Doc"}}]

    result = await DocumentationService(FakeRagClient(tuple(chunks))).answer(
        "question", "token"
    )

    assert json.loads(result) == chunks


def test_load_mcp_config_reports_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL", raising=False)

    with pytest.raises(McpConfigError):
        load_mcp_config()


def test_load_mcp_config_requires_rag_scope_when_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_MCP_REQUIRED_SCOPES", raising=False)

    assert load_mcp_config().required_scopes == ("rag:mcp",)


def test_load_mcp_config_adds_rag_scope_to_custom_scopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_MCP_REQUIRED_SCOPES", "openid,custom")

    assert load_mcp_config().required_scopes == ("rag:mcp", "openid", "custom")


def test_mcp_transport_allows_public_host() -> None:
    assert "mcp.isilograginterne.fr" in TRANSPORT_SECURITY.allowed_hosts


def test_mcp_server_requires_bearer_auth() -> None:
    assert AUTH_SETTINGS.required_scopes == ["rag:mcp"]
    assert AUTH_SETTINGS.resource_server_url is not None
