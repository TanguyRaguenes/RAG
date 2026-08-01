import pytest

from app.api.routers import embed_router
from app.schemas.embed_request_schema import EmbedRequestBase
from app.schemas.embed_text_response_schema import EmbedTextResponseBase
from app.schemas.ingest_bulk_response_schema import IngestBulkResponseBase


@pytest.mark.asyncio
async def test_embed_route_delegates_to_embedding_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = EmbedTextResponseBase(
        duration_ms=12.0,
        duration_human="00:00",
        embeded_texts=[[0.1, 0.2]],
    )

    async def fake_create_embeddings_response(
        texts: list[str], config: dict
    ) -> EmbedTextResponseBase:
        assert texts == ["question"]
        assert config == {"config": True}
        return expected

    monkeypatch.setattr(
        embed_router,
        "create_embeddings_response",
        fake_create_embeddings_response,
    )

    response = await embed_router.embed_route(
        EmbedRequestBase(texts=["question"]),
        {"config": True},
    )

    assert response is expected


@pytest.mark.asyncio
async def test_ingest_bulk_route_delegates_to_ingestion_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = IngestBulkResponseBase(
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        duration="00:01",
        collection_count_before=2,
        collection_count_after=1,
    )

    async def fake_ingest_all_documents(config: dict) -> IngestBulkResponseBase:
        assert config == {"config": True}
        return expected

    monkeypatch.setattr(
        embed_router,
        "ingest_all_documents",
        fake_ingest_all_documents,
    )

    response = await embed_router.ingest_bulk_route({"config": True})

    assert response is expected
