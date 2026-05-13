from app.services.chunk_service import chunk_text


def get_test_config() -> dict:
    return {
        "chunking": {
            "size_chars": 500,
            "overlap_chars": 50,
        }
    }


def test_chunk_text_returns_chunks_with_markdown_context():
    text = """
            # Guide RAG

            ## Installation

            Voici comment installer le projet.
            """

    chunks = chunk_text(text, get_test_config())

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert "CONTEXT : Guide RAG > Installation" in chunks[0]
    assert "CONTENT :" in chunks[0]
    assert "Voici comment installer le projet." in chunks[0]


def test_chunk_text_removes_toc_and_images():
    text = """
        [[_TOC_]]

        # Documentation

        ![schema](image.png)

        Contenu utile.
        """

    chunks = chunk_text(text, get_test_config())
    result = "\n".join(chunks)

    assert "[[_TOC_]]" not in result
    assert "![schema](image.png)" not in result
    assert "Contenu utile." in result


def test_chunk_text_returns_empty_list_when_text_is_empty():
    chunks = chunk_text("", get_test_config())

    assert chunks == []
    # assert 1 == 2
