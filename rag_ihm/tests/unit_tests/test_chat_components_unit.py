from app.components.chat import (
    ROLE_ASSISTANT,
    ROLE_USER,
    _format_similarity,
    _shorten_text,
    build_assistant_message,
    build_user_message,
)


def test_build_user_message_sets_role_and_content() -> None:
    assert build_user_message("Bonjour") == {"role": ROLE_USER, "content": "Bonjour"}


def test_build_assistant_message_uses_defaults_when_optional_fields_are_missing() -> (
    None
):
    result = build_assistant_message({"llm_response": "Réponse"})

    assert result["role"] == ROLE_ASSISTANT
    assert result["content"] == "Réponse"
    assert result["retrieved_documents"] == {}
    assert result["retrieved_chunks"] == []


def test_shorten_text_normalizes_whitespace_and_truncates() -> None:
    assert _shorten_text("un\n\tdeux   trois", limit=20) == "un deux trois"
    assert _shorten_text("abcdef", limit=4) == "abcd..."


def test_format_similarity_formats_float_or_reports_invalid_value() -> None:
    assert _format_similarity("0.876") == "0.88"
    assert _format_similarity(None) == "non disponible"
