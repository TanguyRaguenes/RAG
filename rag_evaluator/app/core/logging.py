import json
import logging
import os
import re
import sys
from datetime import UTC, datetime

MAX_LOG_EVENT_CHARS = 16_384
MAX_LOG_VALUE_CHARS = 2_048
MAX_LOG_COLLECTION_ITEMS = 25
REDACTED = "[REDACTED]"

_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")
_SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"token|password|secret|cookie)\s*[:=]\s*[^\s,;]+"
)
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "apikey",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
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
        """Sérialise un événement borné après redaction des données sensibles.

        Args:
            record: Événement standard produit par le module `logging`.

        Returns:
            Ligne JSON valide adaptée à stdout et Loki.
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": _sanitize_text(record.getMessage()),
            "service": getattr(record, "service", self.default_service_name),
        }

        if record.exc_info:
            log_data["exception"] = _sanitize_text(
                self.formatException(record.exc_info)
            )

        if record.stack_info:
            log_data["stack"] = _sanitize_text(self.formatStack(record.stack_info))

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = _sanitize_value(value, key=key)

        serialized = json.dumps(log_data, default=str, ensure_ascii=False)
        if len(serialized) <= MAX_LOG_EVENT_CHARS:
            return serialized
        return json.dumps(
            {
                "timestamp": log_data["timestamp"],
                "level": log_data["level"],
                "logger": log_data["logger"],
                "message": _truncate(str(log_data["message"]), MAX_LOG_VALUE_CHARS),
                "service": log_data["service"],
                "truncated": True,
            },
            ensure_ascii=False,
        )


def configure_json_logging(default_service_name: str) -> None:
    """Configure les logs JSON sur la sortie standard.

    Args:
        default_service_name: Nom du microservice si SERVICE_NAME n'est pas défini.

    Returns:
        Aucune valeur. Le logger racine est configuré pour Docker, Alloy et Loki.
    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = _resolve_log_level(log_level_name)
    service_name = os.getenv("SERVICE_NAME", default_service_name)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter(service_name))
    handler._rag_json_handler = True

    root_logger = logging.getLogger()
    root_logger.handlers = [
        current_handler
        for current_handler in root_logger.handlers
        if not getattr(current_handler, "_rag_json_handler", False)
    ]
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.setLevel(log_level)
        uvicorn_logger.propagate = False


def _resolve_log_level(log_level_name: str) -> int:
    """Convertit LOG_LEVEL en niveau logging Python, avec INFO par défaut."""
    if log_level_name.isdecimal():
        return int(log_level_name)

    log_level = getattr(logging, log_level_name, logging.INFO)
    return log_level if isinstance(log_level, int) else logging.INFO


def _sanitize_value(value: object, *, key: str = "") -> object:
    """Redacte et borne récursivement une valeur structurée de log.

    Args:
        value: Valeur libre fournie via `extra`.
        key: Nom du champ parent utilisé pour détecter les secrets.

    Returns:
        Valeur sérialisable ne contenant pas de secret identifiable.
    """
    if _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, dict):
        items = list(value.items())[:MAX_LOG_COLLECTION_ITEMS]
        return {
            str(item_key): _sanitize_value(item_value, key=str(item_key))
            for item_key, item_value in items
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [
            _sanitize_value(item) for item in list(value)[:MAX_LOG_COLLECTION_ITEMS]
        ]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _sanitize_text(str(value))


def _sanitize_text(value: str) -> str:
    """Masque les credentials reconnaissables et borne une chaîne.

    Args:
        value: Message, stacktrace ou valeur textuelle à sécuriser.

    Returns:
        Chaîne redactée et tronquée si nécessaire.
    """
    redacted = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", value)
    redacted = _SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}={REDACTED}",
        redacted,
    )
    return _truncate(redacted, MAX_LOG_VALUE_CHARS)


def _is_sensitive_key(key: str) -> bool:
    """Indique si un nom de champ représente vraisemblablement un secret."""
    normalized = key.casefold().replace("-", "").replace("_", "")
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _truncate(value: str, limit: int) -> str:
    """Tronque une chaîne tout en signalant explicitement la réduction."""
    if len(value) <= limit:
        return value
    return f"{value[: limit - 14]}...[TRUNCATED]"
