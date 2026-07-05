from app.api.routers import collections_router
from app.domain.models.retrieve_chunks_request_model import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrievedChunksModelBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase


def test_save_items_route_delegates_to_service(monkeypatch) -> None:
    calls = []

    def fake_save_items(items, repository):
        calls.append((items, repository))
        return SaveItemsResponseBase(
            collection_count_before=0,
            collection_count_after=1,
            saved_items=[{"id": "id", "chunk": "doc", "metadatas": {}}],
        )

    monkeypatch.setattr(collections_router, "save_items", fake_save_items)
    items = VectorStoreItemsBase(ids=["id"], documents=["doc"], embeddings=[[0.1]], metadatas=[{}])
    repository = object()

    response = collections_router.save_items_route(items, repository)

    assert response.collection_count_after == 1
    assert calls == [(items, repository)]


def test_retrieve_chunk_route_delegates_to_service(monkeypatch) -> None:
    calls = []

    def fake_retrieve_chunks(config, collection, embeded_question, repository):
        calls.append((config, collection, embeded_question, repository))
        return RetrievedChunksModelBase(chunks=[])

    monkeypatch.setattr(collections_router, "retrieve_chunks", fake_retrieve_chunks)
    config = {"retriever": {}}
    collection = object()
    repository = object()

    response = collections_router.retrieve_chunk_route(
        RetrieveChunksRequestBase(embeded_question=[0.1]),
        collection,
        config,
        repository,
    )

    assert response.chunks == []
    assert calls == [(config, collection, [0.1], repository)]


def test_delete_collection_route_returns_contract_message(monkeypatch) -> None:
    calls = []

    def fake_delete_collection(config, repository):
        calls.append((config, repository))

    monkeypatch.setattr(collections_router, "delete_collection", fake_delete_collection)
    config = {"collection": {"name": "wiki"}}
    repository = object()

    assert collections_router.delete_collection_route(repository, config) == "Collection : bien supprimée."
    assert calls == [(config, repository)]
