import json
import logging
import sys
from types import SimpleNamespace

import pytest

from app.components import common
from app.core import logging as app_logging
from app.core.errors import RagApiError


def test_render_api_error_logs_safe_fields_and_clears_session_on_401(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_streamlit = SimpleNamespace(
        session_state={
            "auth_access_token": "secret-token",
            "chat_messages": [{"content": "private question"}],
        },
        errors=[],
    )
    fake_streamlit.error = fake_streamlit.errors.append
    monkeypatch.setattr(common, "st", fake_streamlit)
    error = RagApiError(
        "La session a expiré.",
        {
            "status_code": 401,
            "url": "https://secret.example",
            "question": "private question",
        },
        code="http_401",
    )

    with caplog.at_level(logging.DEBUG, logger=common.__name__):
        common.render_api_error(error)

    assert fake_streamlit.session_state == {}
    assert fake_streamlit.errors == ["La session a expiré."]
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert caplog.records[0].details == {"status_code": 401}
    assert "secret-token" not in caplog.text
    assert "private question" not in caplog.text
    assert "secret.example" not in caplog.text


def test_json_formatter_redacts_sensitive_fields_and_bounds_values() -> None:
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        __file__,
        1,
        "stable message",
        (),
        None,
    )
    record.payload = {
        "access_token": "secret-token",
        "state": "secret-state",
        "code": "secret-code",
        "question": "private question",
        "generated_prompt": "private prompt",
        "retrieved_chunks": ["private chunk"],
        "commentaire": "private comment",
        "feedback_comment_1": "private nested comment",
        "oauth_state": "private nested state",
        "status_code": 503,
        "error_code": "http_503",
        "safe_text": "x" * 1000,
    }

    rendered = app_logging.JsonLogFormatter("rag_ihm").format(record)
    payload = json.loads(rendered)

    assert payload["payload"]["status_code"] == 503
    assert payload["payload"]["error_code"] == "http_503"
    assert payload["payload"]["safe_text"].endswith("...")
    for forbidden in (
        "secret-token",
        "secret-state",
        "secret-code",
        "private question",
        "private prompt",
        "private chunk",
        "private comment",
        "private nested comment",
        "private nested state",
    ):
        assert forbidden not in rendered


def test_json_formatter_does_not_serialize_exception_message() -> None:
    try:
        raise RuntimeError("private response body and secret-token")
    except RuntimeError:
        record = logging.LogRecord(
            "test",
            logging.ERROR,
            __file__,
            1,
            "stable message",
            (),
            sys.exc_info(),
        )

    rendered = app_logging.JsonLogFormatter("rag_ihm").format(record)

    assert "RuntimeError" in rendered
    assert "private response body" not in rendered
    assert "secret-token" not in rendered


def test_configure_json_logging_is_idempotent_on_streamlit_reruns() -> None:
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = list(root_logger.handlers)
    try:
        app_logging.configure_json_logging("rag_ihm")
        app_logging.configure_json_logging("rag_ihm")

        handlers = [
            handler
            for handler in root_logger.handlers
            if getattr(handler, app_logging._HANDLER_MARKER, False)
        ]
        assert len(handlers) == 1
    finally:
        root_logger.handlers[:] = original_handlers
        root_logger.setLevel(original_level)
