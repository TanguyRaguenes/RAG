import pytest
from app.core.config import load_config
from app.dal.clients.embedding_client import embed


@pytest.mark.asyncio
async def test_embed_returns_non_empty_float_vector():
    config = load_config()
    config["embedding"]["url"] = "http://localhost:11434/api/embed"
    vectors = await embed(["hello"], config=config, is_query=True)
    assert isinstance(vectors, list)
    assert len(vectors) == 1
    assert all(isinstance(x, float) for x in vectors[0])
