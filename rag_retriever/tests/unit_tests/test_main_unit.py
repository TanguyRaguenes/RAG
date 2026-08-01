import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.api.dependencies import get_config, get_vector_store_repository
from app.api.routers import collections_router
from app.core.exceptions import RetrievalFormatException


def _client() -> TestClient:
    """Construit un client de l'application réelle avec dépendances isolées."""
    main_module.app.dependency_overrides[get_config] = lambda: {
        "collection": {"name": "wiki"},
        "retriever": {
            "top_k": 3,
            "minimum_similarity": 0.5,
            "minimum_number_of_chunks": 1,
        },
    }
    main_module.app.dependency_overrides[get_vector_store_repository] = object
    return TestClient(main_module.app, raise_server_exceptions=False)


def test_main_app_returns_safe_custom_error_and_logs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_retrieval(
        config: dict, embedding: list[float], repository: object
    ) -> None:
        raise RetrievalFormatException(
            internal_details={
                "path": "private/wiki.md",
                "url": "http://chroma:8000",
            }
        )

    exception_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(collections_router, "retrieve_chunks", fail_retrieval)
    monkeypatch.setattr(
        main_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append(args),
    )

    response = _client().post("/retrieve_chunks", json={"embeded_question": [0.1]})

    assert response.status_code == 502
    assert response.json() == {
        "slug": "ERR_RETRIEVAL_FORMAT",
        "message": "Le stockage vectoriel a retourné une réponse invalide.",
        "details": {},
    }
    assert "private" not in response.text
    assert "chroma" not in response.text
    assert len(exception_calls) == 1
    main_module.app.dependency_overrides.clear()


def test_main_app_returns_neutral_payload_for_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_retrieval(
        config: dict, embedding: list[float], repository: object
    ) -> None:
        raise RuntimeError("secret Chroma endpoint: http://chroma:8000")

    exception_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(collections_router, "retrieve_chunks", fail_retrieval)
    monkeypatch.setattr(
        main_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append(args),
    )

    response = _client().post("/retrieve_chunks", json={"embeded_question": [0.1]})

    assert response.status_code == 500
    assert response.json() == {
        "slug": "ERR_INTERNAL",
        "message": "Une erreur interne est survenue.",
        "details": {},
    }
    assert "secret" not in response.text
    assert "chroma:8000" not in response.text
    assert len(exception_calls) == 1
    main_module.app.dependency_overrides.clear()
