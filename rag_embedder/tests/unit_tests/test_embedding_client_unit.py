from types import TracebackType
from typing import ClassVar, Self

import pytest
from app.core.exceptions import EmbeddingServiceException
from app.dal.clients import embedding_client
from app.dal.clients.embedding_client import embed


class FakeResponse:
    payload: ClassVar[dict] = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict]] = []

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
        return FakeResponse()


@pytest.mark.asyncio
async def test_embed_raises_exception_when_service_is_unreachable() -> None:

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
    assert e.message == "Le service d'embeddings est temporairement indisponible."
    assert e.internal_details == {
        "operation": "embed",
        "error_type": "connect_error",
    }
    assert e.to_dict()["details"] == {}
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_coordinate",
    [True, "0.1", float("nan"), float("inf"), float("-inf")],
    ids=["bool", "str", "nan", "positive-infinity", "negative-infinity"],
)
async def test_embed_rejects_invalid_coordinates_before_success_metric(
    monkeypatch: pytest.MonkeyPatch,
    invalid_coordinate: object,
) -> None:
    config = {
        "embedding": {
            "url": "http://embedder/embeddings",
            "model": "test-model",
            "prefixes": {"query": "Q: ", "document": "D: "},
        }
    }
    successful_requests: list[tuple[str, float]] = []
    monkeypatch.setattr(embedding_client.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        FakeResponse,
        "payload",
        {"embeddings": [[invalid_coordinate]]},
    )
    monkeypatch.setattr(
        embedding_client,
        "_record_request_success",
        lambda operation, duration: successful_requests.append((operation, duration)),
    )

    with pytest.raises(EmbeddingServiceException):
        await embed(["hello"], config=config, is_query=True)

    assert successful_requests == []


@pytest.mark.asyncio
async def test_embed_accepts_integer_coordinates_as_real_numbers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = {
        "embedding": {
            "url": "http://embedder/embeddings",
            "model": "test-model",
            "prefixes": {"query": "Q: ", "document": "D: "},
        }
    }
    monkeypatch.setattr(embedding_client.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(FakeResponse, "payload", {"embeddings": [[1, 2]]})

    result = await embed(["hello"], config=config, is_query=False)

    assert result == [[1.0, 2.0]]
