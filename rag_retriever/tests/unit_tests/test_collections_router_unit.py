import pytest

from app.api.routers import collections_router
from app.domain.models.retrieve_chunks_request_model import (
    RetrieveChunksRequestBase,
    RetrieveDocumentChunksRequestBase,
)
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
    items = VectorStoreItemsBase(
        ids=["id"], documents=["doc"], embeddings=[[0.1]], metadatas=[{}]
    )
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


def test_retrieve_document_chunks_route_delegates_to_service(monkeypatch) -> None:
    calls = []

    def fake_retrieve_document_chunks(collection, paths, repository):
        calls.append((collection, paths, repository))
        return RetrievedChunksModelBase(chunks=[])

    monkeypatch.setattr(
        collections_router, "retrieve_document_chunks", fake_retrieve_document_chunks
    )
    collection = object()
    repository = object()

    response = collections_router.retrieve_document_chunks_route(
        RetrieveDocumentChunksRequestBase(paths=["wiki/a.md"]),
        collection,
        repository,
    )

    assert response.chunks == []
    assert calls == [(collection, ["wiki/a.md"], repository)]


def test_delete_collection_route_returns_contract_message(monkeypatch) -> None:
    calls = []

    def fake_delete_collection(config, repository):
        calls.append((config, repository))

    monkeypatch.setattr(collections_router, "delete_collection", fake_delete_collection)
    config = {"collection": {"name": "wiki"}}
    repository = object()

    assert (
        collections_router.delete_collection_route(repository, config)
        == "Collection : bien supprimée."
    )
    assert calls == [(config, repository)]


def test_save_items_route_records_and_reraises_service_error(monkeypatch) -> None:
    def fake_save_items(items, repository):
        raise RuntimeError("save failed")

    monkeypatch.setattr(collections_router, "save_items", fake_save_items)
    items = VectorStoreItemsBase(
        ids=["id"], documents=["doc"], embeddings=[[0.1]], metadatas=[{}]
    )

    with pytest.raises(RuntimeError, match="save failed"):
        collections_router.save_items_route(items, object())


def test_retrieve_chunk_route_records_and_reraises_service_error(monkeypatch) -> None:
    def fake_retrieve_chunks(config, collection, embeded_question, repository):
        raise RuntimeError("retrieve failed")

    monkeypatch.setattr(collections_router, "retrieve_chunks", fake_retrieve_chunks)

    with pytest.raises(RuntimeError, match="retrieve failed"):
        collections_router.retrieve_chunk_route(
            RetrieveChunksRequestBase(embeded_question=[0.1]),
            object(),
            {"retriever": {}},
            object(),
        )


def test_retrieve_document_chunks_route_records_and_reraises_service_error(
    monkeypatch,
) -> None:
    def fake_retrieve_document_chunks(collection, paths, repository):
        raise RuntimeError("document retrieve failed")

    monkeypatch.setattr(
        collections_router, "retrieve_document_chunks", fake_retrieve_document_chunks
    )

    with pytest.raises(RuntimeError, match="document retrieve failed"):
        collections_router.retrieve_document_chunks_route(
            RetrieveDocumentChunksRequestBase(paths=["wiki/a.md"]),
            object(),
            object(),
        )


def test_delete_collection_route_records_and_reraises_service_error(
    monkeypatch,
) -> None:
    def fake_delete_collection(config, repository):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(collections_router, "delete_collection", fake_delete_collection)

    with pytest.raises(RuntimeError, match="delete failed"):
        collections_router.delete_collection_route(object(), {"collection": {}})
