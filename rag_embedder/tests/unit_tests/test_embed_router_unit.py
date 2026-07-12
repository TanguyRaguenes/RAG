import pytest

from app.api.routers import embed_router
from app.domain.models.document_model import DocumentBase, DocumentsBase
from app.domain.models.embed_request_model import EmbedRequestBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase


@pytest.mark.asyncio
async def test_embed_route_returns_embeddings_and_duration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_service_embed(texts: list[str], config: dict) -> list[list[float]]:
        assert texts == ["question", "autre question"]
        assert config == {"config": True}
        return [[0.1, 0.2], [0.3, 0.4]]

    monkeypatch.setattr(embed_router, "service_embed", fake_service_embed)
    monkeypatch.setattr(embed_router.time, "perf_counter", iter([1.0, 2.2]).__next__)

    response = await embed_router.embed_route(
        EmbedRequestBase(texts=["question", "autre question"]),
        {"config": True},
    )

    assert response.embeded_texts == [[0.1, 0.2], [0.3, 0.4]]
    assert response.duration_ms == 1200.0
    assert response.duration_human == "00:01"


@pytest.mark.asyncio
async def test_ingest_bulk_route_loads_documents_and_returns_saved_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    documents = DocumentsBase(
        documents=[DocumentBase(path="doc.md", content="content")]
    )

    async def fake_load_documents() -> DocumentsBase:
        return documents

    async def fake_ingest_documents(received_documents: DocumentsBase, config: dict):
        assert received_documents is documents
        assert config == {"config": True}
        return SaveItemsResponseBase(
            collection_count_before=0,
            collection_count_after=1,
            saved_items=[{"id": "id", "chunk": "content", "metadatas": {}}],
        )

    monkeypatch.setattr(embed_router, "load_documents", fake_load_documents)
    monkeypatch.setattr(embed_router, "ingest_documents", fake_ingest_documents)
    monkeypatch.setattr(embed_router.time, "perf_counter", iter([1.0, 2.0]).__next__)

    response = await embed_router.ingest_bulk_route({"config": True})

    assert response.duration == "00:01"
    assert response.savedItems.collection_count_after == 1
