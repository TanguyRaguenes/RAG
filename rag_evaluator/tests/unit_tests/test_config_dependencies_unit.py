import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_bearer_token, get_config
from app.core import config as config_module
from app.core.config import EvaluatorConfig, load_admin_groups
from app.core.exceptions import EvaluatorAuthenticationError


def _raw_config() -> dict:
    return {
        "rag_provider": "api",
        "judge_provider": "local",
        "llm": {
            "common": {
                "temperature": 0.1,
                "timeout_seconds": 10,
                "stream": False,
            },
            "local": {
                "provider": "Ollama",
                "endpoint": "http://ollama/v1/chat/completions",
                "model": "test-local",
                "context_window_tokens": 1024,
                "max_output_tokens": 128,
                "max_prompt_chars": 2000,
            },
            "api": {
                "provider": "OpenAi",
                "endpoint": "https://api.openai.com/v1/responses",
                "model": "test-api",
                "max_output_tokens": 128,
                "max_prompt_chars": 4000,
            },
        },
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

    assert config.llm.local.model == "test-local"
    assert config.llm.api.endpoint == "https://api.openai.com/v1/responses"
    assert config.judge_provider == "local"
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
