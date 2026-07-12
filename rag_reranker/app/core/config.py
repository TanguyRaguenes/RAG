import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Charge le fichier de configuration JSON du microservice.

    Returns:
        Dictionnaire de configuration lu depuis le fichier JSON du service.
    """
    with open(_CONFIG_PATH, "r", encoding="utf-8") as jsonFile:
        return json.load(jsonFile)
