import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configure_json_logging() -> None:
    """Configure les logs JSON sur la sortie standard.

    Returns:
        Aucune valeur. Le logger racine est configuré pour écrire sur stdout.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
