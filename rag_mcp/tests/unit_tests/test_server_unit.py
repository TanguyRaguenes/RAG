import json

import pytest

from server import (
    McpConfigError,
    cache_access_token,
    format_retrieved_chunks_response,
    is_cached_token_valid,
    load_mcp_config,
)


def test_is_cached_token_valid_requires_safety_window() -> None:
    assert is_cached_token_valid({"access_token": "abc", "expires_at": 150}, now=100)
    assert not is_cached_token_valid(
        {"access_token": "abc", "expires_at": 120}, now=100
    )
    assert not is_cached_token_valid({"expires_at": 150}, now=100)


def test_cache_access_token_updates_cache_in_place() -> None:
    cache: dict[str, str | int] = {}

    cache_access_token(cache, "token", 123)

    assert cache == {"access_token": "token", "expires_at": 123}


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
