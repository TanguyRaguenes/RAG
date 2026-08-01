import json
import logging

from app.core.logging import JsonLogFormatter, configure_json_logging


def test_json_formatter_redacts_sensitive_fields_and_limits_size() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="safe event",
        args=(),
        exc_info=None,
    )
    record.api_key = "top-secret"
    record.context = {
        "authorization": "Bearer secret",
        "note": "x" * 3000,
    }

    payload = json.loads(JsonLogFormatter("rag_embedder").format(record))

    assert payload["api_key"] == "[REDACTED]"
    assert payload["context"]["authorization"] == "[REDACTED]"
    assert payload["context"]["note"].endswith("...[TRUNCATED]")
    assert len(payload["context"]["note"]) < 3000


def test_json_logging_is_idempotent_and_configures_uvicorn() -> None:
    root_logger = logging.getLogger()
    original_root_handlers = list(root_logger.handlers)
    logger_names = ("uvicorn", "uvicorn.error", "uvicorn.access")
    original_uvicorn_states = {
        logger_name: (
            list(logging.getLogger(logger_name).handlers),
            logging.getLogger(logger_name).level,
            logging.getLogger(logger_name).propagate,
        )
        for logger_name in logger_names
    }
    try:
        configure_json_logging("rag_embedder")
        configure_json_logging("rag_embedder")

        root_handlers = [
            handler for handler in root_logger.handlers if handler.name == "rag_json"
        ]
        assert len(root_handlers) == 1
        for logger_name in logger_names:
            uvicorn_logger = logging.getLogger(logger_name)
            assert uvicorn_logger.handlers == root_handlers
            assert uvicorn_logger.propagate is False
    finally:
        root_logger.handlers = original_root_handlers
        for logger_name, state in original_uvicorn_states.items():
            uvicorn_logger = logging.getLogger(logger_name)
            uvicorn_logger.handlers, uvicorn_logger.level, uvicorn_logger.propagate = (
                state
            )
