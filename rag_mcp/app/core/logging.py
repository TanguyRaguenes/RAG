import json
import logging
import os
import sys
import traceback
from collections.abc import Mapping
from datetime import UTC, datetime

type LogValue = (
    None | bool | int | float | str | list["LogValue"] | dict[str, "LogValue"]
)

MAX_LOG_STRING_LENGTH = 512
MAX_LOG_COLLECTION_ITEMS = 20
MAX_LOG_DEPTH = 4
MAX_LOG_JSON_BYTES = 16_384
_HANDLER_MARKER = "_rag_mcp_json_handler"
_REDACTED = "[REDACTED]"
_TRUNCATED = "[TRUNCATED]"
_SAFE_COMPOUND_LOG_KEYS = frozenset(
    {
        "chunk_count",
        "document_count",
        "error_code",
        "prompt_count",
        "question_count",
        "status_code",
        "token_count",
    }
)
_SENSITIVE_LOG_KEYS = frozenset(
    {
        "authorization",
        "token",
        "secret",
        "code",
        "state",
        "question",
        "prompt",
        "document",
        "chunks",
        "cookies",
        "headers",
    }
)
_UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error", "uvicorn.access")

_RESERVED_LOG_RECORD_ATTRS = set(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
) | {"message", "asctime"}


class JsonLogFormatter(logging.Formatter):
    """Formate les logs applicatifs en JSON exploitable par Loki."""

    def __init__(self, default_service_name: str) -> None:
        super().__init__()
        self.default_service_name = default_service_name

    def format(self, record: logging.LogRecord) -> str:
        message = (
            "HTTP access"
            if record.name == "uvicorn.access"
            else _truncate_string(record.getMessage())
        )
        log_data: dict[str, LogValue] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": _truncate_string(record.name),
            "message": message,
            "service": redact_log_value(
                getattr(record, "service", self.default_service_name),
                key="service",
            ),
        }

        if record.exc_info:
            log_data["exception"] = _format_safe_exception(record)

        if record.stack_info:
            log_data["stack"] = _truncate_string(self.formatStack(record.stack_info))

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = redact_log_value(value, key=key)

        return _serialize_bounded_json(log_data)


def configure_json_logging(default_service_name: str) -> None:
    """Configure les logs JSON sur la sortie standard.

    Args:
        default_service_name: Nom du microservice si SERVICE_NAME n'est pas défini.

    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = _resolve_log_level(log_level_name)
    service_name = os.getenv("SERVICE_NAME", default_service_name)

    root_logger = logging.getLogger()
    handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, _HANDLER_MARKER, False)
    ]
    if handlers:
        handler = handlers[0]
        for duplicate in handlers[1:]:
            root_logger.removeHandler(duplicate)
    else:
        handler = logging.StreamHandler(sys.stdout)
        setattr(handler, _HANDLER_MARKER, True)
        root_logger.addHandler(handler)

    formatter = JsonLogFormatter(service_name)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    root_logger.setLevel(log_level)
    _configure_uvicorn_logging(formatter, log_level, service_name)


def _resolve_log_level(log_level_name: str) -> int:
    """Convertit LOG_LEVEL en niveau logging Python, avec INFO par défaut."""
    if log_level_name.isdecimal():
        return int(log_level_name)

    log_level = getattr(logging, log_level_name, logging.INFO)
    return log_level if isinstance(log_level, int) else logging.INFO


def redact_log_value(
    value: object,
    *,
    key: str | None = None,
    depth: int = 0,
) -> LogValue:
    """Redacte les clés sensibles et borne récursivement les valeurs de log.

    Args:
        value: Valeur candidate provenant d'un champ structuré.
        key: Nom du champ parent utilisé par la politique de redaction.
        depth: Profondeur courante du parcours récursif.

    Returns:
        Valeur JSON sûre et bornée ou marqueur explicite de redaction.
    """
    if key and _is_sensitive_key(key):
        return _REDACTED
    if depth >= MAX_LOG_DEPTH:
        return _TRUNCATED
    if isinstance(value, str):
        return _truncate_string(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Mapping):
        redacted_mapping: dict[str, LogValue] = {}
        for item_key, item_value in list(value.items())[:MAX_LOG_COLLECTION_ITEMS]:
            key_text = str(item_key)
            redacted_mapping[_truncate_string(key_text)] = redact_log_value(
                item_value,
                key=key_text,
                depth=depth + 1,
            )
        return redacted_mapping
    if isinstance(value, list | tuple | set):
        return [
            redact_log_value(item, depth=depth + 1)
            for item in list(value)[:MAX_LOG_COLLECTION_ITEMS]
        ]
    return _truncate_string(str(value))


def _format_safe_exception(record: logging.LogRecord) -> dict[str, LogValue]:
    """Formate le type et la pile sans sérialiser le message de l'exception.

    Args:
        record: Enregistrement contenant l'exception inattendue.

    Returns:
        Type d'erreur et emplacements de pile bornés, sans corps ni token.
    """
    exception_type, _, traceback_value = record.exc_info or (None, None, None)
    frames = traceback.extract_tb(traceback_value, limit=20) if traceback_value else []
    return {
        "type": exception_type.__name__ if exception_type else "Exception",
        "stack": [
            _truncate_string(f"{frame.filename}:{frame.lineno} in {frame.name}")
            for frame in frames
        ],
    }


def _configure_uvicorn_logging(
    formatter: JsonLogFormatter,
    log_level: int,
    service_name: str,
) -> None:
    """Aligne les loggers Uvicorn actuels et leur future configuration MCP.

    Args:
        formatter: Formatter JSON partagé avec le handler applicatif.
        log_level: Niveau résolu depuis la configuration applicative.
        service_name: Nom de service injecté dans les logs Uvicorn futurs.
    """
    for logger_name in _UVICORN_LOGGER_NAMES:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(log_level)
        if uvicorn_logger.handlers:
            for uvicorn_handler in uvicorn_logger.handlers:
                uvicorn_handler.setFormatter(formatter)
                uvicorn_handler.setLevel(log_level)
            uvicorn_logger.propagate = False
        else:
            uvicorn_logger.propagate = True

    try:
        from uvicorn.config import LOGGING_CONFIG
    except ImportError:  # pragma: no cover - Uvicorn est une dépendance de production.
        return

    LOGGING_CONFIG.setdefault("formatters", {})["rag_json"] = {
        "()": JsonLogFormatter,
        "default_service_name": service_name,
    }
    for handler_name in ("default", "access"):
        handler_config = LOGGING_CONFIG.get("handlers", {}).get(handler_name)
        if isinstance(handler_config, dict):
            handler_config["formatter"] = "rag_json"
            handler_config["stream"] = "ext://sys.stdout"


def _is_sensitive_key(key: str) -> bool:
    """Détecte les clés sensibles exactes ou composées."""
    normalized = key.strip().lower().replace("-", "_")
    if normalized in _SAFE_COMPOUND_LOG_KEYS:
        return False
    return any(
        normalized == sensitive
        or normalized.startswith(f"{sensitive}_")
        or normalized.endswith(f"_{sensitive}")
        or f"_{sensitive}_" in normalized
        for sensitive in _SENSITIVE_LOG_KEYS
    )


def _truncate_string(value: str) -> str:
    """Borne une chaîne individuelle avant sa sérialisation JSON."""
    if len(value) <= MAX_LOG_STRING_LENGTH:
        return value
    return f"{value[:MAX_LOG_STRING_LENGTH].rstrip()}..."


def _serialize_bounded_json(log_data: dict[str, LogValue]) -> str:
    """Sérialise un log sans dépasser la limite JSON globale.

    Args:
        log_data: Champs déjà redacted et bornés individuellement.

    Returns:
        Document JSON valide dont la taille UTF-8 respecte la limite globale.
    """
    serialized = json.dumps(log_data, ensure_ascii=False)
    if len(serialized.encode("utf-8")) <= MAX_LOG_JSON_BYTES:
        return serialized

    exception = log_data.get("exception")
    exception_type = exception.get("type") if isinstance(exception, dict) else None
    fallback: dict[str, LogValue] = {
        "timestamp": log_data.get("timestamp"),
        "level": log_data.get("level"),
        "logger": log_data.get("logger"),
        "message": log_data.get("message"),
        "service": log_data.get("service"),
        "truncated": True,
    }
    if isinstance(exception_type, str):
        fallback["exception"] = {"type": exception_type}

    serialized = json.dumps(fallback, ensure_ascii=False)
    if len(serialized.encode("utf-8")) <= MAX_LOG_JSON_BYTES:
        return serialized

    return json.dumps(
        {"message": _TRUNCATED, "truncated": True},
        ensure_ascii=False,
    )
