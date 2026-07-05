import httpx
import pytest

from app.core.exceptions import RetrievalServiceException
from app.dal.clients import retriever_client
from app.domain.models.vector_store_item_model import VectorStoreItemsBase


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = ""):
        self.payload = payload
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("POST", "http://retriever/save_items")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    calls: list[dict] = []
    response = FakeResponse({"saved": True})

    def __init__(self, timeout: int):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return self.response


def _items() -> VectorStoreItemsBase:
    return VectorStoreItemsBase(
        ids=["id-1"],
        documents=["doc"],
        embeddings=[[0.1]],
        metadatas=[{"path": "doc.md"}],
    )


@pytest.mark.asyncio
async def test_save_items_requires_retriever_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_RETRIEVER_INGEST_DOCUMENTS_URL", raising=False)

    with pytest.raises(RetrievalServiceException) as exc_info:
        await retriever_client.save_items(_items())

    assert "retriever" in exc_info.value.message


@pytest.mark.asyncio
async def test_save_items_posts_vector_store_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({"saved": True})
    monkeypatch.setenv(
        "RAG_RETRIEVER_INGEST_DOCUMENTS_URL", "http://retriever/save_items"
    )
    monkeypatch.setattr(retriever_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await retriever_client.save_items(_items())

    assert result == {"saved": True}
    assert FakeAsyncClient.calls == [
        {
            "url": "http://retriever/save_items",
            "json": _items().model_dump(),
            "timeout": 180,
        }
    ]


@pytest.mark.asyncio
async def test_save_items_wraps_http_status_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({}, status_code=503, text="down")
    monkeypatch.setenv(
        "RAG_RETRIEVER_INGEST_DOCUMENTS_URL", "http://retriever/save_items"
    )
    monkeypatch.setattr(retriever_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(RetrievalServiceException) as exc_info:
        await retriever_client.save_items(_items())

    assert exc_info.value.message == "Erreur HTTP 503"
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
