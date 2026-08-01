from types import TracebackType
from typing import ClassVar, Self

import httpx
import pytest
from app.core.exceptions import RetrievalServiceException
from app.dal.clients import retriever_client
from app.schemas.vector_store_items_schema import VectorStoreItemsBase


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = "") -> None:
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
    calls: ClassVar[list[dict]] = []
    response = FakeResponse(
        {
            "collection_count_before": 0,
            "collection_count_after": 1,
            "saved_items": [
                {
                    "id": "id-1",
                    "chunk": "doc",
                    "metadatas": {
                        "path": "doc.md",
                        "title": "Doc",
                        "chunk_index": 0,
                        "related_links": "",
                        "has_links": False,
                    },
                }
            ],
        }
    )

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        return False

    async def post(self, url: str, json: dict) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return self.response


def _items() -> VectorStoreItemsBase:
    return VectorStoreItemsBase(
        ids=["id-1"],
        documents=["doc"],
        embeddings=[[0.1]],
        metadatas=[{"path": "doc.md", "title": "Doc", "chunk_index": 0}],
    )


@pytest.mark.asyncio
async def test_save_items_requires_retriever_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_RETRIEVER_INGEST_DOCUMENTS_URL", raising=False)

    with pytest.raises(RetrievalServiceException) as exc_info:
        await retriever_client.save_items(_items())

    assert exc_info.value.message == (
        "Le service de stockage est temporairement indisponible."
    )
    assert exc_info.value.internal_details["error_type"] == "missing_url"


@pytest.mark.asyncio
async def test_save_items_posts_vector_store_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse(
        {
            "collection_count_before": 0,
            "collection_count_after": 1,
            "saved_items": [
                {
                    "id": "id-1",
                    "chunk": "doc",
                    "metadatas": {
                        "path": "doc.md",
                        "title": "Doc",
                        "chunk_index": 0,
                    },
                }
            ],
        }
    )
    monkeypatch.setenv(
        "RAG_RETRIEVER_INGEST_DOCUMENTS_URL", "http://retriever/save_items"
    )
    monkeypatch.setattr(retriever_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await retriever_client.save_items(_items())

    assert result.collection_count_after == 1
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

    assert exc_info.value.message == (
        "Le service de stockage est temporairement indisponible."
    )
    assert exc_info.value.internal_details["status_code"] == 503
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
