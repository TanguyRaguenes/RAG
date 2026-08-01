import pytest
from app.api.routers.rerank_router import rerank_chunks_route
from app.schemas.rerank_chunks_request_schema import RerankChunksRequestBase
from app.schemas.rerank_chunks_response_schema import RerankChunksResponseBase


class FakeRerankService:
    def __init__(self) -> None:
        self.payload: RerankChunksRequestBase | None = None

    async def execute(
        self, payload: RerankChunksRequestBase
    ) -> RerankChunksResponseBase:
        self.payload = payload
        return RerankChunksResponseBase(
            duration_ms=12.0,
            duration_human="00:00",
            reranked_chunks=[{**payload.chunks[0].model_dump(), "rerank_score": 0.9}],
        )


@pytest.mark.asyncio
async def test_route_only_delegates_validated_payload() -> None:
    payload = RerankChunksRequestBase(
        question="Question",
        chunks=[
            {
                "id": "chunk-1",
                "document": "doc",
                "metadata": {"title": "Doc"},
                "similarity": 0.7,
            }
        ],
    )
    service = FakeRerankService()

    response = await rerank_chunks_route(payload, service)

    assert service.payload is payload
    assert response.reranked_chunks[0].rerank_score == 0.9
