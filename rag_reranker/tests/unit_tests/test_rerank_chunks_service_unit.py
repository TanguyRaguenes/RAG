import pytest

from app.core.config import RerankerConfig
from app.core.exceptions import RerankingResponseFormatException
from app.schemas.rerank_chunks_request_schema import ChunkModelBase
from app.services.rerank_chunks_service import RerankChunksService


def _config(top_k: int = 2, minimum_rerank_score: float = 0.005) -> RerankerConfig:
    return RerankerConfig.model_validate(
        {
            "reranking": {
                "provider": "tei",
                "url": "http://tei/rerank",
                "model": "model",
                "top_k": top_k,
                "minimum_rerank_score": minimum_rerank_score,
            }
        }
    )


def _chunks() -> list[ChunkModelBase]:
    return [
        ChunkModelBase(id="chunk-1", document="first", metadata={}, similarity=0.8),
        ChunkModelBase(id="chunk-2", document="second", metadata={}, similarity=0.9),
        ChunkModelBase(id="chunk-3", document="third", metadata={}, similarity=0.7),
    ]


class FakeRerankingClient:
    def __init__(self, scores: dict[int, float]) -> None:
        self.scores = scores
        self.calls = 0

    async def score(
        self, question: str, chunks: list[ChunkModelBase]
    ) -> dict[int, float]:
        assert question == "Question"
        self.calls += 1
        return self.scores


class FailingRerankingClient:
    async def score(
        self, question: str, chunks: list[ChunkModelBase]
    ) -> dict[int, float]:
        raise RuntimeError("programming bug")


@pytest.mark.asyncio
async def test_service_orders_scores_and_applies_top_k() -> None:
    service = RerankChunksService(
        _config(top_k=2), FakeRerankingClient({0: 0.2, 1: 0.95, 2: 0.5})
    )

    response = await service.rerank("Question", _chunks())

    assert [chunk.id for chunk in response] == ["chunk-2", "chunk-3"]
    assert response[0].rerank_score == 0.95


@pytest.mark.asyncio
async def test_service_excludes_chunks_with_a_score_displayed_as_zero() -> None:
    service = RerankChunksService(
        _config(top_k=3, minimum_rerank_score=0.2),
        FakeRerankingClient({0: 0.95, 1: 0.199, 2: 0.2}),
    )

    response = await service.rerank("Question", _chunks())

    assert [chunk.id for chunk in response] == ["chunk-1", "chunk-3"]
    assert all(chunk.rerank_score >= 0.2 for chunk in response)


@pytest.mark.asyncio
async def test_service_does_not_call_provider_for_empty_chunks() -> None:
    client = FakeRerankingClient({})

    response = await RerankChunksService(_config(), client).rerank("Question", [])

    assert response == []
    assert client.calls == 0


@pytest.mark.asyncio
async def test_service_uses_similarity_when_scores_are_equal() -> None:
    service = RerankChunksService(
        _config(top_k=3), FakeRerankingClient({0: 0.5, 1: 0.5, 2: 0.5})
    )

    response = await service.rerank("Question", _chunks())

    assert [chunk.id for chunk in response] == ["chunk-2", "chunk-1", "chunk-3"]


@pytest.mark.asyncio
async def test_service_never_invents_missing_score() -> None:
    service = RerankChunksService(
        _config(top_k=3), FakeRerankingClient({0: 0.5, 1: 0.4})
    )

    with pytest.raises(RerankingResponseFormatException, match="exhaustive"):
        await service.rerank("Question", _chunks())


@pytest.mark.asyncio
async def test_service_does_not_mask_unexpected_client_bug() -> None:
    service = RerankChunksService(_config(), FailingRerankingClient())

    with pytest.raises(RuntimeError, match="programming bug"):
        await service.rerank("Question", _chunks())
