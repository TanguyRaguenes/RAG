import pytest

from app.api.routers import rerank_router
from app.domain.models.rerank_chunks_request_model import RerankChunksRequestBase


@pytest.mark.asyncio
async def test_rerank_chunks_route_returns_chunks_and_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_service_rerank_chunks(question: str, chunks: list[dict], config: dict):
        assert question == "Question"
        assert chunks[0]["id"] == "chunk-1"
        assert config == {"config": True}
        return [dict(chunks[0], rerank_score=0.9)]

    monkeypatch.setattr(rerank_router, "service_rerank_chunks", fake_service_rerank_chunks)
    monkeypatch.setattr(rerank_router.time, "perf_counter", iter([1.0, 2.2]).__next__)

    response = await rerank_router.rerank_chunks_route(
        RerankChunksRequestBase(
            question="Question",
            chunks=[
                {
                    "id": "chunk-1",
                    "document": "doc",
                    "metadata": {"title": "Doc"},
                    "similarity": 0.7,
                }
            ],
        ),
        {"config": True},
    )

    assert response.duration_ms == 1200.0
    assert response.duration_human == "00:01"
    assert response.reranked_chunks[0].rerank_score == 0.9
