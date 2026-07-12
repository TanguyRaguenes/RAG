from app.services.prompt_builder_service import build_context, build_judge_messages


def test_build_context_includes_path_chunk_and_respects_max_chars() -> None:
    chunks = [
        {"metadata": {"path": "a.md", "chunk": 0}, "document": "Court"},
        {"metadata": {"path": "b.md", "chunk": 1}, "document": "B" * 200},
    ]

    context = build_context(chunks, max_chars=60)

    assert "[a.md | chunk 0]" in context
    assert "Court" in context
    assert "b.md" not in context


def test_build_judge_messages_contains_question_answers_context_and_format_rules() -> (
    None
):
    messages = build_judge_messages(
        question="Question ?",
        generated_answer="Réponse générée",
        reference_answer="Réponse attendue",
        retrieved_chunks=[
            {"metadata": {"path": "doc.md", "chunk": 1}, "document": "Contexte"}
        ],
    )

    assert messages[0]["role"] == "system"
    assert "expert evaluator" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "Question ?" in messages[1]["content"]
    assert "Réponse générée" in messages[1]["content"]
    assert "Réponse attendue" in messages[1]["content"]
    assert "Contexte" in messages[1]["content"]
