import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as jsonFile:
        return json.load(jsonFile)
