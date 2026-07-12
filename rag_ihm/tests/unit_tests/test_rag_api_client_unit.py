from app.services.rag_api_client import (
    ChatApiConfig,
    _auth_headers,
    _docs_url,
    _extract_error_message,
    _truncate,
    _usage_url,
)


def test_usage_url_reuses_orchestrator_base_url() -> None:
    config = ChatApiConfig(
        health_url="http://orchestrator/",
        ask_question_url="http://orchestrator/ask_question",
    )

    assert _usage_url(config, "/usage/quota/me") == (
        "http://orchestrator/usage/quota/me"
    )


def test_docs_url_appends_docs_once() -> None:
    assert _docs_url("http://service") == "http://service/docs"
    assert _docs_url("http://service/docs") == "http://service/docs"


def test_extract_error_message_prefers_nested_original_exception() -> None:
    assert (
        _extract_error_message(
            {"original_exception": {"message": "Erreur métier"}, "detail": "fallback"}
        )
        == "Erreur métier"
    )


def test_extract_error_message_falls_back_to_known_keys() -> None:
    assert _extract_error_message({"detail": "Détail"}) == "Détail"
    assert _extract_error_message({}) == "Le service RAG a retourné une erreur."


def test_truncate_limits_long_values() -> None:
    assert _truncate("abc", limit=3) == "abc"
    assert _truncate("abcdef", limit=4) == "abcd..."


def test_auth_headers_builds_bearer_header() -> None:
    assert _auth_headers("token") == {"Authorization": "Bearer token"}
