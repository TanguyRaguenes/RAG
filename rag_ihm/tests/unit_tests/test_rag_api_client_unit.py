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


def test_health_url_is_explicit_and_never_appends_docs() -> None:
    assert _docs_url("http://service/health") == "http://service/health"
    assert _docs_url("http://service/docs") == "http://service/docs"


def test_orchestrator_base_url_ignores_query_and_trailing_slash() -> None:
    config = ChatApiConfig(
        health_url="http://orchestrator/health",
        ask_question_url="http://orchestrator/api/ask_question/?debug=true",
    )

    assert config.base_url == "http://orchestrator/api"


def test_extract_error_message_never_exposes_backend_details() -> None:
    assert _extract_error_message({"detail": "secret backend"}) == (
        "Le service RAG a retourné une erreur."
    )
    assert _extract_error_message({}) == "Le service RAG a retourné une erreur."


def test_truncate_limits_long_values() -> None:
    assert _truncate("abc", limit=3) == "abc"
    assert _truncate("abcdef", limit=4) == "abcd..."


def test_auth_headers_builds_bearer_header() -> None:
    assert _auth_headers("token") == {"Authorization": "Bearer token"}
