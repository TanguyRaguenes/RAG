import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    RerankerContainerCustomException,
    RerankingResponseFormatException,
    register_exception_handlers,
)


class RerankingRequestException(RerankerContainerCustomException):
    """Erreur 422 de test permettant de vérifier le niveau WARNING."""

    STATUS_CODE = 422


def _build_test_app() -> FastAPI:
    """Construit une API ASGI isolée avec les handlers de production."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/controlled")
    def controlled_failure() -> None:
        raise RerankingRequestException(
            message="Requête invalide",
            internal_message="Bearer private-token",
        )

    @test_app.get("/provider")
    def provider_failure() -> None:
        raise RerankingResponseFormatException(message="Réponse invalide")

    @test_app.get("/unexpected")
    def unexpected_failure() -> None:
        raise RuntimeError("Bearer private-token")

    return test_app


def test_custom_handler_returns_stable_payload_and_warns_for_4xx(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.core.exceptions"):
        response = TestClient(_build_test_app()).get("/controlled")

    assert response.status_code == 422
    assert response.json() == {
        "slug": "ERR_RERANKING_SERVICE",
        "message": "Requête invalide",
        "details": {},
    }
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_custom_5xx_handler_does_not_attach_a_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.core.exceptions"):
        response = TestClient(_build_test_app()).get("/provider")

    assert response.status_code == 502
    controlled_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "controlled_request_failure"
    ]
    assert controlled_records
    assert controlled_records[-1].exc_info is None


def test_unexpected_handler_returns_neutral_500_and_logs_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="app.core.exceptions"):
        response = TestClient(_build_test_app(), raise_server_exceptions=False).get(
            "/unexpected"
        )

    assert response.status_code == 500
    assert response.json() == {
        "slug": "ERR_INTERNAL",
        "message": "Une erreur interne est survenue",
        "details": {},
    }
    unexpected_records = [
        record
        for record in caplog.records
        if getattr(record, "event", None) == "unexpected_request_failure"
    ]
    assert unexpected_records[-1].exc_info is not None
