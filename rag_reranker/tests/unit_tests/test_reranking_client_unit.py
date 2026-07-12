import pytest

from app.core.exceptions import (
    RerankingResponseFormatException,
    RerankingServiceException,
)
from app.dal.clients import reranking_client


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


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
        return FakeResponse([{"index": 0, "score": 0.8}])


def _config() -> dict:
    return {
        "reranking": {
            "url": "http://tei-reranker/rerank",
            "model": "BAAI/bge-reranker-base",
            "timeout_seconds": 12,
            "max_chunk_chars": 10,
        }
    }


@pytest.mark.asyncio
async def test_score_chunks_posts_prompt_and_returns_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(reranking_client.httpx, "AsyncClient", FakeAsyncClient)

    scores = await reranking_client.score_chunks(
        "Question",
        [{"document": "long document content", "metadata": {"title": "Doc"}}],
        _config(),
    )

    assert scores == {0: 0.8}
    assert FakeAsyncClient.calls[0]["url"] == "http://tei-reranker/rerank"
    assert FakeAsyncClient.calls[0]["timeout"] == 12
    assert FakeAsyncClient.calls[0]["json"] == {
        "query": "Question",
        "texts": ["long docum"],
        "raw_scores": False,
        "return_text": False,
    }


@pytest.mark.asyncio
async def test_score_chunks_raises_exception_when_service_is_unreachable() -> None:
    config = _config()
    config["reranking"]["url"] = "http://127.0.0.1:1/rerank"

    with pytest.raises(RerankingServiceException) as exc:
        await reranking_client.score_chunks(
            "Question",
            [{"document": "doc", "metadata": {}}],
            config,
        )

    assert exc.value.STATUS_CODE == 503
    assert exc.value.SLUG.value == "ERR_RERANKING_SERVICE"
    assert exc.value.__cause__ is not None


def test_parse_scores_raises_exception_when_response_has_invalid_format() -> None:
    with pytest.raises(RerankingResponseFormatException) as exc:
        reranking_client._parse_scores({"unexpected": []}, 1)

    assert exc.value.STATUS_CODE == 502
    assert exc.value.SLUG.value == "ERR_RERANKING_RESPONSE_FORMAT"


def test_parse_scores_clamps_scores_between_zero_and_one() -> None:
    scores = reranking_client._parse_scores(
        [{"index": 0, "score": 1.8}, {"index": 1, "score": -2}],
        2,
    )

    assert scores == {0: 1.0, 1: 0.0}
