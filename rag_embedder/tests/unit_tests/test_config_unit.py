import json

from app.core import config as config_module


def test_load_config_reads_json_file(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"embedding": {"model": "test"}}), encoding="utf-8"
    )
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    assert config_module.load_config() == {"embedding": {"model": "test"}}
