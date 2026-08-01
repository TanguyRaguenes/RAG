import json
import logging
import os
import sys
import traceback
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
            log_data["exception"] = _format_safe_exception(record)

        if record.stack_info:
            log_data["stack"] = self.formatStack(record.stack_info)

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = value

        return json.dumps(log_data, default=str, ensure_ascii=False)


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

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)


def _resolve_log_level(log_level_name: str) -> int:
    """Convertit LOG_LEVEL en niveau logging Python, avec INFO par défaut."""
    if log_level_name.isdecimal():
        return int(log_level_name)

    log_level = getattr(logging, log_level_name, logging.INFO)
    return log_level if isinstance(log_level, int) else logging.INFO


def _format_safe_exception(record: logging.LogRecord) -> dict[str, object]:
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
            f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in frames
        ],
    }
