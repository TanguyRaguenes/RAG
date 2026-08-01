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
                    "minimum_rerank_score": 0.125,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    loaded_config = config_module.load_config().reranking

    assert loaded_config.model == "test"
    assert loaded_config.minimum_rerank_score == 0.125
