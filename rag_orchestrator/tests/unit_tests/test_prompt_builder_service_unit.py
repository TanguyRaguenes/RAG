from app.services.prompt_builder_service import build_context, build_prompt


def test_build_context_includes_chunk_metadata_and_stops_at_character_limit() -> None:
    chunks = [
        {
            "metadata": {"title": "Doc A", "path": "a.md", "chunk_index": 0},
            "document": "A" * 10,
        },
        {
            "metadata": {"title": "Doc B", "path": "b.md", "chunk_index": 1},
            "document": "B" * 100,
        },
    ]

    context = build_context(chunks, max_prompt_chars=80)

    assert "SOURCE: Doc A" in context
    assert "PATH: a.md" in context
    assert "CHUNK: 0" in context
    assert "Doc B" not in context


def test_build_prompt_uses_context_and_refusal_instruction_when_chunks_exist() -> None:
    prompt = build_prompt(
        "Question ?",
        [
            {
                "metadata": {"title": "Doc", "path": "doc.md", "chunk_index": 0},
                "document": "Info",
            }
        ],
        max_prompt_chars=500,
    )

    assert prompt[0]["role"] == "system"
    assert "Je ne sais pas" in prompt[0]["content"]
    assert "CONTEXTE:" in prompt[1]["content"]
    assert "Question ?" in prompt[1]["content"]


def test_build_prompt_falls_back_to_generic_assistant_without_context() -> None:
    prompt = build_prompt("Question ?", [], max_prompt_chars=500)

    assert prompt == [
        {"role": "system", "content": "Tu es un assistant utile et concis."},
        {"role": "user", "content": "Question ?"},
    ]
