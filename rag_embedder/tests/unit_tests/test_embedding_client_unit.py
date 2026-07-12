import pytest
from app.core.exceptions import EmbeddingServiceException
from app.dal.clients import embedding_client
from app.dal.clients.embedding_client import embed


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}


class FakeAsyncClient:
    calls: list[dict] = []

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return FakeResponse()


@pytest.mark.asyncio
async def test_embed_raises_exception_when_service_is_unreachable():

    config = {
        "embedding": {
            "url": "http://127.0.0.1:1/embeddings",
            "model": "test-model",
            "prefixes": {"query": "Q: ", "document": "D: "},
        }
    }

    with pytest.raises(EmbeddingServiceException) as exc:
        await embed(["hello"], config=config, is_query=True)

    e = exc.value
    assert e.STATUS_CODE == 503
    assert e.SLUG.value == "ERR_EMBEDDING_SERVICE"
    assert "Impossible de se connecter" in e.message
    assert e.details["url"] == config["embedding"]["url"]
    assert e.__cause__ is not None


@pytest.mark.asyncio
async def test_embed_posts_prefixed_texts_and_returns_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    config = {
        "embedding": {
            "url": "http://embedder/embeddings",
            "model": "test-model",
            "prefixes": {"query": "Q: ", "document": "D: "},
        }
    }

    monkeypatch.setattr(embedding_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await embed(["hello", "world"], config=config, is_query=True)

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert FakeAsyncClient.calls == [
        {
            "url": "http://embedder/embeddings",
            "json": {"model": "test-model", "input": ["Q: hello", "Q: world"]},
            "timeout": 120,
        }
    ]
