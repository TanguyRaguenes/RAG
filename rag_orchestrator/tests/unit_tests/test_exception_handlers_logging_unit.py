import json
import logging

import httpx
import pytest
from fastapi import FastAPI

from app.api.exception_handlers import (
    application_exception_handler,
    unexpected_exception_handler,
)
from app.core.exceptions import (
    ApplicationError,
    ErrorSlug,
    QuestionQuotaExceededError,
    QuotaExceededError,
    QuotaInactiveError,
    UsageSessionValidationError,
)
from app.core.logging import JsonLogFormatter, configure_json_logging


@pytest.mark.asyncio
async def test_asgi_handlers_return_public_contract_and_keep_native_validation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(ApplicationError, application_exception_handler)
    test_app.add_exception_handler(Exception, unexpected_exception_handler)

    @test_app.get("/expected")
    async def expected_route() -> None:
        raise UsageSessionValidationError("private validation reason")

    @test_app.get("/unexpected")
    async def unexpected_route() -> None:
        raise RuntimeError("private question and http://internal/service")

    @test_app.get("/validated")
    async def validated_route(count: int) -> dict[str, int]:
        return {"count": count}

    transport = httpx.ASGITransport(app=test_app, raise_app_exceptions=False)
    caplog.set_level(logging.WARNING, logger="app.api.exception_handlers")
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        expected = await client.get("/expected")
        unexpected = await client.get("/unexpected")
        validation = await client.get("/validated", params={"count": "invalid"})

    assert expected.status_code == 400
    assert expected.json() == {
        "slug": "ERR_USAGE_SESSION_INVALID",
        "message": "La session d'usage demandée n'est pas valide.",
        "details": {},
    }
    assert unexpected.status_code == 500
    assert unexpected.json() == {
        "slug": ErrorSlug.INTERNAL.value,
        "message": "Une erreur interne est survenue.",
        "details": {},
    }
    assert validation.status_code == 422
    assert "detail" in validation.json()
    events = [getattr(record, "event", None) for record in caplog.records]
    assert events.count("application_error") == 1
    assert events.count("unexpected_error") == 1


@pytest.mark.parametrize(
    ("exception", "status_code", "slug"),
    [
        (UsageSessionValidationError(), 400, "ERR_USAGE_SESSION_INVALID"),
        (QuestionQuotaExceededError(), 429, "ERR_QUESTION_QUOTA_EXCEEDED"),
        (QuotaExceededError(100, 100), 429, "ERR_QUOTA_EXCEEDED"),
        (QuotaInactiveError(), 429, "ERR_QUOTA_INACTIVE"),
    ],
)
def test_business_error_contracts_are_stable(
    exception: ApplicationError,
    status_code: int,
    slug: str,
) -> None:
    assert exception.STATUS_CODE == status_code
    assert exception.to_dict() == {
        "slug": slug,
        "message": exception.PUBLIC_MESSAGE,
        "details": {},
    }


def test_json_formatter_redacts_sensitive_fields_urls_and_exception_messages() -> None:
    formatter = JsonLogFormatter("rag_orchestrator")
    try:
        raise ValueError("private token http://internal/private")
    except ValueError as exception:
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Dependency failed at http://internal/private",
            args=(),
            exc_info=(type(exception), exception, exception.__traceback__),
        )
    record.question = "sensitive question"
    record.context = {
        "authorization": "Bearer secret-token",
        "prompt": "sensitive prompt",
        "token_count": 42,
    }

    payload = json.loads(formatter.format(record))
    encoded = json.dumps(payload)

    assert payload["question"] == "[REDACTED]"
    assert payload["context"]["authorization"] == "[REDACTED]"
    assert payload["context"]["prompt"] == "[REDACTED]"
    assert payload["context"]["token_count"] == 42
    assert payload["exception"]["type"] == "ValueError"
    assert "http://" not in encoded
    assert "sensitive question" not in encoded
    assert "sensitive prompt" not in encoded
    assert "secret-token" not in encoded


def test_json_logging_configuration_is_idempotent_and_preserves_test_handlers() -> None:
    root_logger = logging.getLogger()
    logger_names = ("uvicorn", "uvicorn.error", "uvicorn.access")
    original_root_handlers = list(root_logger.handlers)
    original_uvicorn_state = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).propagate,
        )
        for name in logger_names
    }
    sentinel = logging.NullHandler()
    root_logger.handlers = [sentinel]

    try:
        configure_json_logging("rag_orchestrator")
        configure_json_logging("rag_orchestrator")

        managed_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_rag_json_handler", False)
        ]
        assert sentinel in root_logger.handlers
        assert len(managed_handlers) == 1
        for name in logger_names:
            assert logging.getLogger(name).handlers == managed_handlers
    finally:
        root_logger.handlers = original_root_handlers
        for name, (handlers, propagate) in original_uvicorn_state.items():
            logging.getLogger(name).handlers = handlers
            logging.getLogger(name).propagate = propagate


def test_json_formatter_bounds_large_events() -> None:
    formatter = JsonLogFormatter("rag_orchestrator")
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    for index in range(20):
        setattr(record, f"payload_{index}", "x" * 5000)

    encoded = formatter.format(record)
    payload = json.loads(encoded)

    assert len(encoded) <= 16384
    assert payload["truncated"] is True
