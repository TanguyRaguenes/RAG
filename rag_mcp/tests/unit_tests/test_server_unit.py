import json

import pytest

from config import McpConfigError, load_mcp_config
from rag_client import format_retrieved_chunks_response
from server import mcp


def test_format_retrieved_chunks_response_returns_empty_message() -> None:
    assert format_retrieved_chunks_response({"retrieved_chunks": []}) == (
        "Aucune information trouvée."
    )


def test_format_retrieved_chunks_response_serializes_chunks() -> None:
    chunks = [{"document": "Résumé", "metadata": {"title": "Doc"}}]

    result = format_retrieved_chunks_response({"retrieved_chunks": chunks})

    assert json.loads(result) == chunks


def test_load_mcp_config_reports_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_ORCHESTRATOR_RETRIEVE_CHUNKS_URL", raising=False)

    with pytest.raises(McpConfigError):
        load_mcp_config()


def test_mcp_transport_allows_public_host() -> None:
    assert "mcp.isilograginterne.fr" in mcp.settings.transport_security.allowed_hosts


def test_mcp_server_requires_bearer_auth() -> None:
    assert mcp.settings.auth is not None
    assert mcp.settings.auth.required_scopes == ["rag:mcp"]
    assert mcp.settings.auth.resource_server_url is not None
