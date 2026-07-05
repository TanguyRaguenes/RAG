import json
from types import SimpleNamespace

from app.api.dependencies import get_config
from app.core import config as config_module


def test_get_config_returns_app_state_config() -> None:
    config = {"llm": {}}
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=config)))

    assert get_config(request) is config


def test_load_config_reads_json_file(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"llm": {"model": "test"}}), encoding="utf-8")
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    assert config_module.load_config() == {"llm": {"model": "test"}}
