import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    DatasetException,
    EvaluatorAuthenticationError,
    register_exception_handlers,
)


def _build_test_app() -> FastAPI:
    """Construit une API ASGI isolée avec les handlers de production."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/authentication")
    def authentication_failure() -> None:
        raise EvaluatorAuthenticationError(message="Bearer requis")

    @test_app.get("/dataset")
    def dataset_failure() -> None:
        raise DatasetException(
            message="Dataset invalide",
            details={"errors": 1},
            internal_details={"dataset_path": "C:/private/dataset.json"},
        )

    @test_app.get("/unexpected")
    def unexpected_failure() -> None:
        raise RuntimeError("secret=private-value")

    return test_app


def test_authentication_handler_returns_bearer_challenge_and_stable_payload() -> None:
    response = TestClient(_build_test_app()).get("/authentication")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {
        "slug": "ERR_EVALUATOR_AUTHENTICATION",
        "message": "Bearer requis",
        "details": {},
    }


def test_dataset_handler_warns_without_exposing_dataset_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.core.exceptions"):
        response = TestClient(_build_test_app()).get("/dataset")

    assert response.status_code == 422
    assert response.json() == {
        "slug": "ERR_DATASET",
        "message": "Dataset invalide",
        "details": {"errors": 1},
    }
    assert "C:/private/dataset.json" not in response.text
    assert any(record.levelno == logging.WARNING for record in caplog.records)


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
