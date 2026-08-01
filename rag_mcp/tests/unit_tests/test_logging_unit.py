import copy
import json
import logging
import sys

from app.core import logging as app_logging
from uvicorn.config import LOGGING_CONFIG


def test_configure_json_logging_is_idempotent_and_preserves_external_handlers() -> None:
    root_logger = logging.getLogger()
    original_root_handlers = list(root_logger.handlers)
    original_root_level = root_logger.level
    original_uvicorn_config = copy.deepcopy(LOGGING_CONFIG)
    uvicorn_states = {
        name: (
            list(logging.getLogger(name).handlers),
            logging.getLogger(name).level,
            logging.getLogger(name).propagate,
        )
        for name in app_logging._UVICORN_LOGGER_NAMES
    }
    external_handler = logging.NullHandler()

    try:
        root_logger.handlers[:] = [
            handler
            for handler in root_logger.handlers
            if not getattr(handler, app_logging._HANDLER_MARKER, False)
        ]
        root_logger.addHandler(external_handler)

        app_logging.configure_json_logging("rag_mcp")
        app_logging.configure_json_logging("rag_mcp")

        managed_handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, app_logging._HANDLER_MARKER, False)
        ]
        assert len(managed_handlers) == 1
        assert external_handler in root_logger.handlers
        assert LOGGING_CONFIG["handlers"]["default"]["formatter"] == "rag_json"
        assert LOGGING_CONFIG["handlers"]["access"]["formatter"] == "rag_json"
        for logger_name in app_logging._UVICORN_LOGGER_NAMES:
            uvicorn_logger = logging.getLogger(logger_name)
            assert not any(
                getattr(handler, app_logging._HANDLER_MARKER, False)
                for handler in uvicorn_logger.handlers
            )
    finally:
        root_logger.handlers[:] = original_root_handlers
        root_logger.setLevel(original_root_level)
        LOGGING_CONFIG.clear()
        LOGGING_CONFIG.update(original_uvicorn_config)
        for logger_name, (handlers, level, propagate) in uvicorn_states.items():
            uvicorn_logger = logging.getLogger(logger_name)
            uvicorn_logger.handlers[:] = handlers
            uvicorn_logger.setLevel(level)
            uvicorn_logger.propagate = propagate


def test_json_formatter_redacts_nested_values_and_bounds_collections() -> None:
    record = logging.LogRecord(
        "app.test",
        logging.INFO,
        __file__,
        1,
        "stable message",
        (),
        None,
    )
    record.payload = {
        "authorization": "Bearer secret-token",
        "nested": {
            "access_token": "secret-token",
            "client_secret": "private-secret",
            "oauth_code": "private-code",
            "oauth_state": "private-state",
            "user_question": "private question",
            "generated_prompt": "private prompt",
            "source_document": "private document",
            "retrieved_chunks": ["private chunk"],
            "request_cookies": {"session": "private cookie"},
            "response_headers": {"set-cookie": "private header"},
            "safe": "x" * 2_000,
        },
        "items": list(range(100)),
    }

    rendered = app_logging.JsonLogFormatter("rag_mcp").format(record)
    payload = json.loads(rendered)["payload"]

    assert payload["authorization"] == "[REDACTED]"
    assert payload["nested"]["access_token"] == "[REDACTED]"
    assert payload["nested"]["client_secret"] == "[REDACTED]"
    assert payload["nested"]["oauth_code"] == "[REDACTED]"
    assert payload["nested"]["oauth_state"] == "[REDACTED]"
    assert payload["nested"]["user_question"] == "[REDACTED]"
    assert payload["nested"]["generated_prompt"] == "[REDACTED]"
    assert payload["nested"]["source_document"] == "[REDACTED]"
    assert payload["nested"]["retrieved_chunks"] == "[REDACTED]"
    assert payload["nested"]["request_cookies"] == "[REDACTED]"
    assert payload["nested"]["response_headers"] == "[REDACTED]"
    assert len(payload["nested"]["safe"]) <= app_logging.MAX_LOG_STRING_LENGTH + 3
    assert len(payload["items"]) == app_logging.MAX_LOG_COLLECTION_ITEMS
    assert "secret-token" not in rendered
    assert "private question" not in rendered
    assert "private prompt" not in rendered
    assert "private document" not in rendered
    assert "private chunk" not in rendered
    assert "private cookie" not in rendered
    assert "private header" not in rendered


def test_json_formatter_bounds_global_json_and_hides_exception_message() -> None:
    try:
        raise RuntimeError("secret-token private question")
    except RuntimeError:
        record = logging.LogRecord(
            "app.test",
            logging.ERROR,
            __file__,
            1,
            "stable message",
            (),
            sys.exc_info(),
        )

    record.large_payload = {
        f"safe_{index}": ["é" * 2_000 for _ in range(100)] for index in range(100)
    }
    rendered = app_logging.JsonLogFormatter("rag_mcp").format(record)
    payload = json.loads(rendered)

    assert len(rendered.encode("utf-8")) <= app_logging.MAX_LOG_JSON_BYTES
    assert payload["truncated"] is True
    assert payload["exception"]["type"] == "RuntimeError"
    assert "secret-token" not in rendered
    assert "private question" not in rendered


def test_uvicorn_access_log_does_not_serialize_request_query() -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1", "GET", "/mcp?code=secret&state=private", "1.1", 200),
        None,
    )

    rendered = app_logging.JsonLogFormatter("rag_mcp").format(record)
    payload = json.loads(rendered)

    assert payload["message"] == "HTTP access"
    assert "secret" not in rendered
    assert "private" not in rendered
