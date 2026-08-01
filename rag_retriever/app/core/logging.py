import json
import logging
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

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

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "prompt",
    "document",
    "embedding",
)
_MAX_STRING_LENGTH = 2048
_MAX_COLLECTION_ITEMS = 50
_REDACTED = "[REDACTED]"
_TRUNCATED = "...[TRUNCATED]"


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
            "message": record.getMessage(),
            "service": getattr(record, "service", self.default_service_name),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack"] = self.formatStack(record.stack_info)

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = value

        return json.dumps(_sanitize_value(log_data), ensure_ascii=False)


class DynamicStdoutHandler(logging.StreamHandler):
    """Écrit vers le stdout courant, y compris sous capture de tests."""

    def emit(self, record: logging.LogRecord) -> None:
        """Résout stdout au moment exact de l'émission.

        Args:
            record: Enregistrement Python à formater et écrire.
        """
        self.stream = sys.stdout
        super().emit(record)


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

    handler = DynamicStdoutHandler()
    handler.name = "rag_json"
    handler.setFormatter(JsonLogFormatter(service_name))

    root_logger = logging.getLogger()
    root_logger.handlers = [
        current_handler
        for current_handler in root_logger.handlers
        if current_handler.name != "rag_json"
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


def _sanitize_value(value: object, key: str = "") -> object:
    """Nettoie récursivement une valeur avant sa sérialisation JSON.

    Args:
        value: Valeur structurée provenant du message ou des champs `extra`.
        key: Clé parente utilisée pour détecter les données sensibles.

    Returns:
        Valeur sérialisable, expurgée et bornée en taille.
    """
    normalized_key = key.lower().replace("-", "_")
    if any(part in normalized_key for part in _SENSITIVE_KEY_PARTS):
        return _REDACTED
    if isinstance(value, str):
        if len(value) <= _MAX_STRING_LENGTH:
            return value
        return f"{value[:_MAX_STRING_LENGTH]}{_TRUNCATED}"
    if isinstance(value, Mapping):
        return {
            str(child_key): _sanitize_value(child_value, str(child_key))
            for child_key, child_value in list(value.items())[:_MAX_COLLECTION_ITEMS]
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sanitized = [
            _sanitize_value(item, key) for item in value[:_MAX_COLLECTION_ITEMS]
        ]
        if len(value) > _MAX_COLLECTION_ITEMS:
            sanitized.append(_TRUNCATED)
        return sanitized
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _sanitize_value(str(value), key)
