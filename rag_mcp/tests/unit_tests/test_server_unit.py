import json

import pytest
from config import McpConfigError, load_mcp_config
from rag_client import format_retrieved_chunks_response
from server import AUTH_SETTINGS, TRANSPORT_SECURITY


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
    assert "mcp.isilograginterne.fr" in TRANSPORT_SECURITY.allowed_hosts


def test_mcp_server_requires_bearer_auth() -> None:
    assert AUTH_SETTINGS.required_scopes == ["rag:mcp"]
    assert AUTH_SETTINGS.resource_server_url is not None
