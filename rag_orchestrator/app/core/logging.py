import json
import logging
import os
import re
import sys
import traceback
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import Enum
from types import TracebackType

_MAX_VALUE_LENGTH = 2048
_MAX_COLLECTION_ITEMS = 50
_MAX_LOG_LENGTH = 16384
_MAX_TRACEBACK_FRAMES = 20
_MANAGED_HANDLER_ATTRIBUTE = "_rag_json_handler"
_SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "chunks",
    "content",
    "document",
    "documents",
    "embedding",
    "embeddings",
    "password",
    "prompt",
    "question",
    "response_text",
    "secret",
    "token",
}
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+\-/]+=*")
_URL_PATTERN = re.compile(r"https?://[^\s\"']+")
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
    """Formate et borne les logs JSON après redaction des données sensibles."""

    def __init__(self, default_service_name: str) -> None:
        """Configure le service ajouté aux événements sans champ explicite.

        Args:
            default_service_name: Nom stable du microservice émetteur.
        """
        super().__init__()
        self.default_service_name = default_service_name

    def format(self, record: logging.LogRecord) -> str:
        """Sérialise un événement sans inclure le message brut d'une exception.

        Args:
            record: Événement produit par le module standard :mod:`logging`.

        Returns:
            Objet JSON borné et sûr pour stdout, Loki et les tests.
        """
        message = (
            "HTTP access" if record.name == "uvicorn.access" else record.getMessage()
        )
        log_data: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": _sanitize_value(message),
            "service": _sanitize_value(
                getattr(record, "service", self.default_service_name)
            ),
        }

        if record.exc_info:
            log_data["exception"] = _format_exception(record.exc_info)

        if record.stack_info:
            log_data["stack"] = _truncate_text(record.stack_info)

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_ATTRS or key in log_data:
                continue
            log_data[key] = _redact_field(key, value)

        encoded = json.dumps(log_data, default=str, ensure_ascii=False)
        if len(encoded) <= _MAX_LOG_LENGTH:
            return encoded

        minimal_log = {
            "timestamp": log_data["timestamp"],
            "level": log_data["level"],
            "logger": log_data["logger"],
            "message": _truncate_text(str(log_data["message"]), 512),
            "service": log_data["service"],
            "truncated": True,
        }
        return json.dumps(minimal_log, ensure_ascii=False)


def configure_json_logging(default_service_name: str) -> None:
    """Configure une fois stdout et les loggers Uvicorn avec le même JSON.

    Args:
        default_service_name: Nom du microservice si ``SERVICE_NAME`` est absent.
    """
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = _resolve_log_level(log_level_name)
    service_name = os.getenv("SERVICE_NAME", default_service_name)
    root_logger = logging.getLogger()
    handler = _get_or_create_managed_handler(root_logger)
    handler.setFormatter(JsonLogFormatter(service_name))
    root_logger.setLevel(log_level)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.setLevel(log_level)
        uvicorn_logger.propagate = False


def _get_or_create_managed_handler(root_logger: logging.Logger) -> logging.Handler:
    """Réutilise le handler du service sans supprimer ceux installés par les tests.

    Args:
        root_logger: Logger racine recevant les événements applicatifs.

    Returns:
        Handler stdout appartenant à cette configuration JSON.
    """
    managed_handlers = [
        handler
        for handler in root_logger.handlers
        if getattr(handler, _MANAGED_HANDLER_ATTRIBUTE, False)
    ]
    if managed_handlers:
        handler = managed_handlers[0]
        for duplicate in managed_handlers[1:]:
            root_logger.removeHandler(duplicate)
        return handler

    handler = logging.StreamHandler(sys.stdout)
    setattr(handler, _MANAGED_HANDLER_ATTRIBUTE, True)
    root_logger.addHandler(handler)
    return handler


def _redact_field(key: str, value: object) -> object:
    """Masque une valeur lorsque son nom désigne du contenu sensible.

    Args:
        key: Nom du champ structuré à examiner.
        value: Valeur associée au champ.

    Returns:
        Marqueur de redaction ou valeur récursivement assainie.
    """
    normalized_key = key.lower().replace("-", "_")
    if normalized_key in _SENSITIVE_KEYS or normalized_key.endswith("_secret"):
        return "[REDACTED]"
    return _sanitize_value(value)


def _sanitize_value(value: object) -> object:
    """Assainit récursivement une valeur arbitraire et borne sa taille.

    Args:
        value: Valeur scalaire ou collection issue d'un champ ``extra``.

    Returns:
        Valeur sérialisable dont les secrets et contenus longs sont supprimés.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return _truncate_text(
            _URL_PATTERN.sub(
                "[REDACTED_URL]", _BEARER_PATTERN.sub("Bearer [REDACTED]", value)
            )
        )
    if isinstance(value, Mapping):
        items = list(value.items())[:_MAX_COLLECTION_ITEMS]
        return {str(key): _redact_field(str(key), item) for key, item in items}
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [_sanitize_value(item) for item in value[:_MAX_COLLECTION_ITEMS]]
    if isinstance(value, bytes | bytearray):
        return "[BINARY]"
    if value is None or isinstance(value, bool | int | float):
        return value
    return _truncate_text(type(value).__name__)


def _format_exception(
    exc_info: tuple[type[BaseException], BaseException, TracebackType | None],
) -> dict[str, object]:
    """Résume le type et la pile sans appeler ``str(exception)``.

    Args:
        exc_info: Triplet exception fourni par le module :mod:`logging`.

    Returns:
        Type d'erreur et emplacements de pile sans message dynamique.
    """
    exception_type, _, traceback_value = exc_info
    frames = traceback.extract_tb(traceback_value)[-_MAX_TRACEBACK_FRAMES:]
    return {
        "type": exception_type.__name__,
        "frames": [
            f"{frame.filename}:{frame.lineno} in {frame.name}" for frame in frames
        ],
    }


def _truncate_text(value: str, limit: int = _MAX_VALUE_LENGTH) -> str:
    """Borne une chaîne avec un marqueur explicite.

    Args:
        value: Texte déjà assaini.
        limit: Longueur maximale conservée.

    Returns:
        Texte original ou version tronquée.
    """
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...[TRUNCATED]"


def _resolve_log_level(log_level_name: str) -> int:
    """Convertit ``LOG_LEVEL`` en niveau Python, avec INFO par défaut.

    Args:
        log_level_name: Nom ou valeur numérique du niveau demandé.

    Returns:
        Niveau reconnu par :mod:`logging`.
    """
    if log_level_name.isdecimal():
        return int(log_level_name)

    log_level = getattr(logging, log_level_name, logging.INFO)
    return log_level if isinstance(log_level, int) else logging.INFO
