import pytest
from app.api.dependencies import get_config, get_vector_store_repository
from app.api.routers import collections_router
from app.schemas.retrieve_chunks_request_schema import (
    RetrieveChunksRequestBase,
    RetrieveDocumentChunksRequestBase,
)
from app.schemas.retrieve_chunks_response_schema import RetrievedChunksModelBase
from app.schemas.save_items_response_schema import SaveItemsResponseBase
from app.schemas.vector_db_items_schema import VectorStoreItemsBase
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _metadata() -> dict[str, str | int | bool]:
    return {
        "path": "doc.md",
        "title": "Doc",
        "chunk_index": 0,
        "related_links": "",
        "has_links": False,
    }


def _items() -> VectorStoreItemsBase:
    return VectorStoreItemsBase(
        ids=["id"],
        documents=["doc"],
        embeddings=[[0.1]],
        metadatas=[_metadata()],
    )


def test_save_items_route_delegates_to_service(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    def fake_save_items(
        items: VectorStoreItemsBase, config: dict, repository: object
    ) -> SaveItemsResponseBase:
        calls.append((items, config, repository))
        return SaveItemsResponseBase(
            collection_count_before=0,
            collection_count_after=1,
            saved_items=[{"id": "id", "chunk": "doc", "metadatas": _metadata()}],
        )

    monkeypatch.setattr(collections_router, "save_items", fake_save_items)
    repository = object()
    config = {"collection": {"name": "wiki"}}

    response = collections_router.save_items_route(_items(), config, repository)

    assert response.collection_count_after == 1
    assert calls == [(_items(), config, repository)]


def test_retrieve_routes_delegate_without_chroma_collection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, ...]] = []

    def fake_retrieve_chunks(
        config: dict, embedding: list[float], repository: object
    ) -> RetrievedChunksModelBase:
        calls.append(("query", config, embedding, repository))
        return RetrievedChunksModelBase(chunks=[])

    def fake_retrieve_document_chunks(
        config: dict, paths: list[str], repository: object
    ) -> RetrievedChunksModelBase:
        calls.append(("documents", config, paths, repository))
        return RetrievedChunksModelBase(chunks=[])

    monkeypatch.setattr(collections_router, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(
        collections_router,
        "retrieve_document_chunks",
        fake_retrieve_document_chunks,
    )
    config = {"collection": {"name": "wiki"}}
    repository = object()

    collections_router.retrieve_chunk_route(
        RetrieveChunksRequestBase(embeded_question=[0.1]),
        config,
        repository,
    )
    collections_router.retrieve_document_chunks_route(
        RetrieveDocumentChunksRequestBase(paths=[]),
        config,
        repository,
    )

    assert calls == [
        ("query", config, [0.1], repository),
        ("documents", config, [], repository),
    ]


def test_save_items_http_rejects_misaligned_vector_payload() -> None:
    app = FastAPI()
    app.include_router(collections_router.router)
    app.dependency_overrides[get_config] = lambda: {"collection": {"name": "wiki"}}
    app.dependency_overrides[get_vector_store_repository] = object

    response = TestClient(app).post(
        "/save_items",
        json={
            "ids": ["id-1", "id-2"],
            "documents": ["only one"],
            "embeddings": [[0.1], [0.2]],
            "metadatas": [_metadata(), _metadata()],
        },
    )

    assert response.status_code == 422


def test_save_items_http_rejects_empty_delete_obsolete_snapshot() -> None:
    app = FastAPI()
    app.include_router(collections_router.router)
    app.dependency_overrides[get_config] = lambda: {"collection": {"name": "wiki"}}
    app.dependency_overrides[get_vector_store_repository] = object

    response = TestClient(app).post(
        "/save_items",
        json={
            "ids": [],
            "documents": [],
            "embeddings": [],
            "metadatas": [],
            "delete_obsolete": True,
        },
    )

    assert response.status_code == 422
    assert "delete_obsolete requires at least one id" in response.text


def test_save_items_http_preserves_response_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_save_items(
        items: VectorStoreItemsBase, config: dict, repository: object
    ) -> SaveItemsResponseBase:
        return SaveItemsResponseBase(
            collection_count_before=1,
            collection_count_after=1,
            saved_items=[{"id": "id", "chunk": "doc", "metadatas": _metadata()}],
        )

    monkeypatch.setattr(collections_router, "save_items", fake_save_items)
    app = FastAPI()
    app.include_router(collections_router.router)
    app.dependency_overrides[get_config] = lambda: {"collection": {"name": "wiki"}}
    app.dependency_overrides[get_vector_store_repository] = object

    response = TestClient(app).post(
        "/save_items",
        json=_items().model_dump(),
    )

    assert response.status_code == 200
    assert response.json()["saved_items"][0]["metadatas"]["path"] == "doc.md"
