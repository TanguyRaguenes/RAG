from app.services.prompt_builder_service import (
    build_context,
    build_prompt,
    format_chunk_as_markdown,
    parse_chunk_document,
)


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

    context = build_context(chunks, max_prompt_chars=230)

    assert "## Chunk 1 - Doc A" in context
    assert "### Métadonnées" in context
    assert "- **Source** : Doc A" in context
    assert "- **Chemin** : `a.md`" in context
    assert "- **Index du chunk** : 0" in context
    assert "### Extrait documentaire" in context
    assert "Doc B" not in context


def test_format_chunk_as_markdown_uses_readable_fallbacks() -> None:
    chunk = {"metadata": {}, "document": "Info"}

    block = format_chunk_as_markdown(1, chunk)

    assert "## Chunk 1" in block
    assert "- **Source** : Non renseigné" in block
    assert "- **Chemin** : `Non renseigné`" in block
    assert "- **Index du chunk** : Non renseigné" in block
    assert "### Extrait documentaire\n\nInfo" in block


def test_format_chunk_as_markdown_splits_context_and_content_labels() -> None:
    chunk = {
        "metadata": {
            "title": "Commentaires",
            "path": "Commentaires.md",
            "chunk_index": 0,
        },
        "document": "CONTEXT : Introduction\nCONTENT : Le code doit être commenté utilement.",
    }

    block = format_chunk_as_markdown(1, chunk)

    assert "CONTEXT :" not in block
    assert "CONTENT :" not in block
    assert "### Section documentaire\n\nIntroduction" in block
    assert "### Extrait documentaire\n\nLe code doit être commenté utilement." in block


def test_parse_chunk_document_falls_back_to_raw_document() -> None:
    section, content = parse_chunk_document("Info brute")

    assert section is None
    assert content == "Info brute"


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
    assert "La réponse ne se trouve pas" in prompt[0]["content"]
    assert "# Question" in prompt[1]["content"]
    assert "# Contexte documentaire" in prompt[1]["content"]
    assert "# Attendu" in prompt[1]["content"]
    assert "## Chunk 1" in prompt[1]["content"]
    assert "Question ?" in prompt[1]["content"]


def test_build_prompt_keeps_grounding_instructions_without_context() -> None:
    prompt = build_prompt("Question ?", [], max_prompt_chars=500)

    assert prompt[0]["role"] == "system"
    assert (
        "Réponds uniquement à partir du contexte documentaire" in prompt[0]["content"]
    )
    assert "La réponse ne se trouve pas" in prompt[0]["content"]
    assert prompt[1]["role"] == "user"
    assert "# Question\n\nQuestion ?" in prompt[1]["content"]
    assert "# Contexte documentaire" in prompt[1]["content"]
