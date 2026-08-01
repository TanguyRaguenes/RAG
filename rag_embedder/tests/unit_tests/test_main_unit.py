import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.api.dependencies import get_config
from app.api.routers import embed_router
from app.core.exceptions import MarkdownProcessingException


def _empty_config() -> dict[str, object]:
    """Retourne la configuration minimale injectée dans les routes testées."""
    return {}


def _client() -> TestClient:
    """Construit un client sans démarrer les dépendances externes du lifespan."""
    main_module.app.dependency_overrides[get_config] = _empty_config
    return TestClient(main_module.app, raise_server_exceptions=False)


def test_main_app_returns_safe_custom_error_and_logs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_ingestion(config: dict) -> None:
        raise MarkdownProcessingException(
            internal_details={
                "relative_path": "private/wiki.md",
                "url": "http://internal/retriever",
            }
        )

    warning_calls: list[tuple[object, ...]] = []
    exception_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(embed_router, "ingest_all_documents", fail_ingestion)
    monkeypatch.setattr(
        main_module.logger,
        "warning",
        lambda *args, **kwargs: warning_calls.append(args),
    )
    monkeypatch.setattr(
        main_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append(args),
    )

    response = _client().post("/ingest/bulk")

    assert response.status_code == 422
    assert response.json() == {
        "slug": "ERR_MARKDOWN_PROCESSING",
        "message": "Les documents Markdown n'ont pas pu être traités.",
        "details": {},
    }
    assert "private" not in response.text
    assert "internal" not in response.text
    assert len(warning_calls) == 1
    assert exception_calls == []
    main_module.app.dependency_overrides.clear()


def test_main_app_returns_neutral_payload_for_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_embedding(texts: list[str], config: dict) -> None:
        raise RuntimeError("secret provider URL: http://internal/embed")

    exception_calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(embed_router, "create_embeddings_response", fail_embedding)
    monkeypatch.setattr(
        main_module.logger,
        "exception",
        lambda *args, **kwargs: exception_calls.append(args),
    )

    response = _client().post("/embed", json={"texts": ["question"]})

    assert response.status_code == 500
    assert response.json() == {
        "slug": "ERR_INTERNAL",
        "message": "Une erreur interne est survenue.",
        "details": {},
    }
    assert "secret" not in response.text
    assert "internal/embed" not in response.text
    assert len(exception_calls) == 1
    main_module.app.dependency_overrides.clear()
