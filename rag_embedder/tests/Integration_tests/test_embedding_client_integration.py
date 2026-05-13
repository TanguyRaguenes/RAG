import pytest
from app.core.config import load_config
from app.dal.clients.embedding_client import embed_text


@pytest.mark.asyncio
async def test_embed_text_returns_non_empty_float_vector():
    config = load_config()
    config["embedding"]["url"] = "http://localhost:11434/api/embed"
    vectors = await embed_text("hello", config=config, is_query=True)
    assert isinstance(vectors, list)
    assert len(vectors) > 0
    assert all(isinstance(x, float) for x in vectors)
