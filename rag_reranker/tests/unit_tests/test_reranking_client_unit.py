import math
from typing import Any, ClassVar, Self

import httpx
import pytest

from app.core.config import RerankerConfig
from app.core.exceptions import (
    RerankingResponseFormatException,
    RerankingServiceException,
)
from app.dal.clients import reranking_client
from app.dal.clients.reranking_client import TeiRerankingClient, score_chunks
from app.schemas.rerank_chunks_request_schema import ChunkModelBase


def _config() -> RerankerConfig:
    return RerankerConfig.model_validate(
        {
            "reranking": {
                "provider": "tei",
                "url": "http://tei-reranker/rerank",
                "model": "BAAI/bge-reranker-base",
                "top_k": 2,
                "timeout_seconds": 12,
                "max_chunk_chars": 10,
            }
        }
    )


def _chunks(count: int = 2) -> list[ChunkModelBase]:
    return [
        ChunkModelBase(
            id=f"chunk-{index}",
            document=f"long document {index}",
            metadata={},
            similarity=0.5,
        )
        for index in range(count)
    ]


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://tei-reranker/rerank")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self) -> object:
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict[str, Any]]] = []
    response: ClassVar[FakeResponse] = FakeResponse(
        [{"index": 0, "score": 0.8}, {"index": 1, "score": 0.4}]
    )

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def post(self, url: str, json: dict[str, Any]) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "timeout": self.timeout})
        return self.response


@pytest.mark.asyncio
async def test_tei_client_posts_contract_and_returns_exhaustive_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    monkeypatch.setattr(reranking_client.httpx, "AsyncClient", FakeAsyncClient)

    scores = await TeiRerankingClient(_config().reranking).score("Question", _chunks())

    assert scores == {0: 0.8, 1: 0.4}
    assert FakeAsyncClient.calls == [
        {
            "url": "http://tei-reranker/rerank",
            "timeout": 12.0,
            "json": {
                "query": "Question",
                "texts": ["long docum", "long docum"],
                "raw_scores": False,
                "return_text": False,
            },
        }
    ]


@pytest.mark.asyncio
async def test_transport_error_does_not_expose_upstream_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.response = FakeResponse({"secret": "upstream"}, status_code=500)
    monkeypatch.setattr(reranking_client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(RerankingServiceException) as exc_info:
        await TeiRerankingClient(_config().reranking).score("Question", _chunks())

    assert exc_info.value.details == {}
    assert "upstream" not in exc_info.value.message
    FakeAsyncClient.response = FakeResponse(
        [{"index": 0, "score": 0.8}, {"index": 1, "score": 0.4}]
    )


@pytest.mark.parametrize(
    "response",
    [
        [{"index": 0, "score": 0.8}],
        [{"index": 0, "score": 0.8}, {"index": 0, "score": 0.4}],
        [{"index": 0, "score": 0.8}, {"index": 2, "score": 0.4}],
    ],
)
def test_parse_scores_requires_exact_unique_indexes(response: object) -> None:
    with pytest.raises(RerankingResponseFormatException):
        reranking_client._parse_scores(response, 2)


@pytest.mark.parametrize("score", [True, False, math.nan, math.inf, -math.inf])
def test_parse_scores_rejects_bool_and_non_finite_scores(score: object) -> None:
    with pytest.raises(RerankingResponseFormatException):
        reranking_client._parse_scores([{"index": 0, "score": score}], 1)


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_parse_scores_rejects_scores_outside_provider_contract(score: float) -> None:
    with pytest.raises(RerankingResponseFormatException):
        reranking_client._parse_scores([{"index": 0, "score": score}], 1)


def test_parse_scores_accepts_results_envelope() -> None:
    assert reranking_client._parse_scores(
        {"results": [{"index": 0, "score": 0.5}]}, 1
    ) == {0: 0.5}


@pytest.mark.asyncio
async def test_legacy_scoring_boundary_translates_pydantic_validation_error() -> None:
    with pytest.raises(RerankingResponseFormatException) as exc_info:
        await score_chunks("Question", [{"document": "missing fields"}], _config())

    assert exc_info.value.__cause__ is not None
    assert exc_info.value.details == {}
