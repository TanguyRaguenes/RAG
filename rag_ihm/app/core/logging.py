import json
import logging
import os
import sys
import traceback
from datetime import UTC, datetime

type LogValue = (
    None | bool | int | float | str | list["LogValue"] | dict[str, "LogValue"]
)

MAX_LOG_STRING_LENGTH = 512
MAX_LOG_COLLECTION_ITEMS = 20
MAX_LOG_DEPTH = 4
_HANDLER_MARKER = "_rag_ihm_json_handler"
_SAFE_COMPOUND_LOG_KEYS = frozenset({"error_code", "status_code"})
_SENSITIVE_LOG_KEYS = frozenset(
    {
        "authorization",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "client_secret",
        "code",
        "state",
        "question",
        "prompt",
        "generated_prompt",
        "chunk",
        "chunks",
        "retrieved_chunks",
        "comment",
        "comments",
        "commentaire",
        "commentaires",
    }
)

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
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": _truncate_string(record.getMessage()),
            "service": getattr(record, "service", self.default_service_name),
        }

        if record.exc_info:
            log_data["exception"] = _format_safe_exception(record)

        if record.stack_info:
            log_data["stack"] = _truncate_string(self.formatStack(record.stack_info))

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = redact_log_value(value, key=key)

        return json.dumps(log_data, default=str, ensure_ascii=False)


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

    handler.setFormatter(JsonLogFormatter(service_name))
    handler.setLevel(log_level)
    root_logger.setLevel(log_level)


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
    """Retire les contenus sensibles et borne les valeurs structurées.

    Args:
        value: Valeur candidate provenant d'un champ de log.
        key: Nom du champ parent utilisé pour appliquer la politique de redaction.
        depth: Profondeur courante de parcours des collections.

    Returns:
        Valeur sérialisable bornée ou marqueur de redaction.
    """
    if key and _is_sensitive_key(key):
        return "[REDACTED]"
    if depth >= MAX_LOG_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, str):
        return _truncate_string(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, dict):
        items = list(value.items())[:MAX_LOG_COLLECTION_ITEMS]
        return {
            str(item_key): redact_log_value(
                item_value,
                key=str(item_key),
                depth=depth + 1,
            )
            for item_key, item_value in items
        }
    if isinstance(value, list | tuple | set):
        return [
            redact_log_value(item, depth=depth + 1)
            for item in list(value)[:MAX_LOG_COLLECTION_ITEMS]
        ]
    return _truncate_string(str(value))


def _is_sensitive_key(key: str) -> bool:
    """Reconnaît les noms de champs dont la valeur ne doit jamais être loggée."""
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
    """Borne une chaîne afin de limiter le volume et l'exposition accidentelle."""
    if len(value) <= MAX_LOG_STRING_LENGTH:
        return value
    return f"{value[:MAX_LOG_STRING_LENGTH].rstrip()}..."


def _format_safe_exception(record: logging.LogRecord) -> dict[str, LogValue]:
    """Conserve le type et la pile sans reprendre le message de l'exception.

    Args:
        record: Enregistrement contenant une exception inattendue.

    Returns:
        Diagnostic borné qui ne peut contenir ni corps HTTP ni contenu utilisateur.
    """
    exception_type, _, traceback_value = record.exc_info or (None, None, None)
    frames = traceback.extract_tb(traceback_value, limit=20) if traceback_value else []
    return {
        "type": exception_type.__name__ if exception_type else "Exception",
        "stack": [
            f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in frames
        ],
    }
