import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.api.dependencies import get_bearer_token, get_config
from app.core import config as config_module
from app.core.config import EvaluatorConfig, load_admin_groups
from app.core.exceptions import EvaluatorAuthenticationError
from fastapi.security import HTTPAuthorizationCredentials


def _raw_config() -> dict:
    return {
        "llm": {
            "provider": "ollama",
            "url_provider": "http://ollama",
            "model": "test",
            "temperature": 0.1,
            "num_ctx": 1024,
            "max_output_token": 128,
            "timeout_seconds": 10,
        },
        "evaluation_method": {"use_api_openai": False},
    }


def test_get_config_returns_app_state_config() -> None:
    config = EvaluatorConfig.model_validate(_raw_config())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=config)))

    assert get_config(request) is config


def test_get_bearer_token_returns_opaque_credentials() -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="opaque-token"
    )

    assert get_bearer_token(credentials) == "opaque-token"


def test_get_bearer_token_rejects_missing_credentials() -> None:
    with pytest.raises(EvaluatorAuthenticationError):
        get_bearer_token(None)


def test_load_config_reads_json_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_raw_config()), encoding="utf-8")
    monkeypatch.setattr(config_module, "_CONFIG_PATH", config_path)

    config = config_module.load_config()

    assert config.llm.model == "test"
    assert config.evaluation_method.openai_url == (
        "https://api.openai.com/v1/chat/completions"
    )
    assert config.evaluation_method.openai_model == "gpt-4o"
    assert config.rag_provider == "api"


def test_evaluator_config_accepts_explicit_local_rag_provider() -> None:
    raw_config = _raw_config()
    raw_config["rag_provider"] = "local"

    assert EvaluatorConfig.model_validate(raw_config).rag_provider == "local"


def test_load_admin_groups_normalizes_configured_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_EVALUATOR_ADMIN_GROUPS", " RAG_Admin,Ops_Admin ")

    assert load_admin_groups() == frozenset({"rag_admin", "ops_admin"})


def test_load_admin_groups_defaults_to_rag_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAG_EVALUATOR_ADMIN_GROUPS", raising=False)

    assert load_admin_groups() == frozenset({"rag_admin"})
