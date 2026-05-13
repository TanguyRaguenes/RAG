import pytest
from app.core.exceptions import EmbeddingServiceException
from app.dal.clients.embedding_client import embed_text


@pytest.mark.asyncio
async def test_embed_text_raises_exception_when_service_is_unreachable():

    config = {
        "embedding": {
            "url": "http://127.0.0.1:1/embeddings",
            "model": "test-model",
            "prefixes": {"query": "Q: ", "document": "D: "},
        }
    }

    with pytest.raises(EmbeddingServiceException) as exc:
        await embed_text("hello", config=config, is_query=True)

    e = exc.value
    assert e.STATUS_CODE == 503
    assert e.SLUG.value == "ERR_EMBEDDING_SERVICE"
    assert "Impossible de se connecter" in e.message
    assert e.details["url"] == config["embedding"]["url"]
    assert e.__cause__ is not None
