from typing import Self

import pytest
from app.components import chat
from app.components.chat import (
    ROLE_ASSISTANT,
    _format_score,
    _shorten_text,
    _sort_chunks_by_rerank_score,
    build_assistant_message,
)


class _Context:
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.expanders: list[str] = []
        self.markdowns: list[str] = []
        self.json_values: list[object] = []

    def chat_message(self, role: str) -> _Context:
        return _Context()

    def expander(self, label: str) -> _Context:
        self.expanders.append(label)
        return _Context()

    def markdown(self, value: str) -> None:
        self.markdowns.append(value)

    def json(self, value: object) -> None:
        self.json_values.append(value)

    def caption(self, value: str) -> None:
        pass

    def divider(self) -> None:
        pass


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


def test_format_score_formats_float_or_reports_invalid_value() -> None:
    assert _format_score("0.876") == "0.88"
    assert _format_score(None) == "non disponible"


def test_sort_chunks_orders_reranker_scores_and_keeps_invalid_items_last() -> None:
    chunks = [
        {"document": "middle", "rerank_score": 0.5},
        {"document": "missing"},
        {"document": "highest", "rerank_score": "0.9"},
        "invalid",
        {"document": "lowest", "rerank_score": 0.1},
        {"document": "not finite", "rerank_score": float("nan")},
    ]

    sorted_chunks = _sort_chunks_by_rerank_score(chunks)

    assert [
        chunk.get("document") if isinstance(chunk, dict) else chunk
        for chunk in sorted_chunks
    ] == [
        "highest",
        "middle",
        "lowest",
        "missing",
        "invalid",
        "not finite",
    ]


def test_render_sources_displays_sorted_scores_and_separate_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()
    monkeypatch.setattr(chat, "st", fake_streamlit)
    chunks = [
        {
            "document": "Moins pertinent",
            "metadata": {"title": "Second"},
            "rerank_score": 0.2,
            "similarity": 0.8,
        },
        {
            "document": "Plus pertinent",
            "metadata": {"title": "Premier"},
            "rerank_score": 0.9,
            "similarity": 0.4,
        },
    ]

    chat._render_sources(chunks, debug_enabled=True)

    assert fake_streamlit.expanders == [
        "Extraits pertinents (2)",
        "Extraits pertinents - JSON (2)",
    ]
    score_lines = [line for line in fake_streamlit.markdowns if line.startswith("**[")]
    assert "Premier · score reranker 0.90 (score retriever 0.40)" in score_lines[0]
    assert "Second · score reranker 0.20 (score retriever 0.80)" in score_lines[1]
    assert fake_streamlit.json_values == [[chunks[1], chunks[0]]]


def test_render_message_separates_formatted_and_json_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_streamlit = FakeStreamlit()
    monkeypatch.setattr(chat, "st", fake_streamlit)
    prompt = [{"role": "system", "content": "Consigne"}]

    chat.render_chat_message(
        {
            "role": ROLE_ASSISTANT,
            "content": "Réponse",
            "retrieved_chunks": [],
            "generated_prompt": prompt,
        },
        debug_enabled=True,
    )

    assert fake_streamlit.expanders == ["Prompt généré", "Prompt généré - JSON"]
    assert fake_streamlit.json_values == [prompt]
