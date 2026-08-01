import pytest
from app.core.config import load_config
from app.core.exceptions import EmbeddingServiceException
from app.dal.clients.embedding_client import embed


@pytest.mark.asyncio
async def test_embed_returns_non_empty_float_vector() -> None:
    config = load_config()
    config["embedding"]["url"] = "http://localhost:11434/api/embed"
    try:
        vectors = await embed(["hello"], config=config, is_query=True)
    except EmbeddingServiceException as exception:
        pytest.skip(f"Ollama embedding endpoint unavailable: {exception.message}")

    assert isinstance(vectors, list)
    assert len(vectors) == 1
    assert all(isinstance(x, float) for x in vectors[0])
