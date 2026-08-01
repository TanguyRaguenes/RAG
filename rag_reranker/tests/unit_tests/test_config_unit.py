import json
from pathlib import Path

import pytest
from app.core import config as config_module


def test_load_config_reads_json_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "reranking": {
                    "provider": "tei",
                    "url": "http://tei/rerank",
                    "model": "test",
                    "top_k": 5,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    assert config_module.load_config().reranking.model == "test"
