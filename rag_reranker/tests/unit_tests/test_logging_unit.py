import json
import logging
import sys
from typing import Any

from app.core.logging import (
    MAX_LOG_EVENT_CHARS,
    MAX_LOG_VALUE_CHARS,
    JsonLogFormatter,
    configure_json_logging,
)


def test_formatter_redacts_secrets_and_bounds_event_size() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=f"Authorization: Bearer private-token {'x' * 20_000}",
        args=(),
        exc_info=None,
    )
    record.api_key = "private-api-key"
    record.context = {
        "password": "private-password",
        "nested": "access_token=private-access-token",
    }

    serialized = JsonLogFormatter("rag_reranker").format(record)
    payload: dict[str, Any] = json.loads(serialized)

    assert len(serialized) <= MAX_LOG_EVENT_CHARS
    assert len(payload["message"]) <= MAX_LOG_VALUE_CHARS
    assert "private-token" not in serialized
    assert "private-api-key" not in serialized
    assert "private-password" not in serialized
    assert "private-access-token" not in serialized
    assert "[REDACTED]" in serialized


def test_formatter_redacts_exception_text() -> None:
    try:
        raise RuntimeError("secret=private-exception-secret")
    except RuntimeError:
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Unexpected failure",
            args=(),
            exc_info=sys.exc_info(),
        )

    serialized = JsonLogFormatter("rag_reranker").format(record)

    assert "private-exception-secret" not in serialized
    assert "secret=[REDACTED]" in serialized


def test_configuration_is_idempotent_and_formats_uvicorn_logs() -> None:
    root_logger = logging.getLogger()
    logger_names = ("uvicorn", "uvicorn.error", "uvicorn.access")
    root_state = (list(root_logger.handlers), root_logger.level)
    uvicorn_state = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in logger_names
    }

    try:
        configure_json_logging("rag_reranker")
        configure_json_logging("rag_reranker")

        managed_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_rag_json_handler", False)
        ]
        assert len(managed_handlers) == 1
        for name in logger_names:
            handlers = logging.getLogger(name).handlers
            assert handlers == managed_handlers
            assert isinstance(handlers[0].formatter, JsonLogFormatter)
            assert logging.getLogger(name).propagate is False
    finally:
        root_logger.handlers, root_logger.level = root_state
        for name, state in uvicorn_state.items():
            uvicorn_logger = logging.getLogger(name)
            uvicorn_logger.handlers = state[0]
            uvicorn_logger.setLevel(state[1])
            uvicorn_logger.propagate = state[2]
