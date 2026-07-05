import pytest

from app.core.exceptions import EvaluatorClientError
from app.dal.client.judge_client import (
    build_auth_headers,
    build_judge_payload,
    format_judge_response,
)


def test_build_judge_payload_maps_config_to_ollama_options() -> None:
    config = {
        "llm": {
            "model": "judge-model",
            "stream": False,
            "temperature": 0.1,
            "num_ctx": 4096,
            "max_output_token": 512,
        }
    }
    messages = [{"role": "user", "content": "Evaluer"}]

    payload = build_judge_payload(config, messages)

    assert payload == {
        "model": "judge-model",
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
            "num_predict": 512,
        },
    }


def test_build_auth_headers_adds_bearer_token_when_available() -> None:
    assert build_auth_headers("token") == {
        "Content-Type": "application/json",
        "Authorization": "Bearer token",
    }


def test_build_auth_headers_without_token_keeps_content_type_only() -> None:
    assert build_auth_headers(None) == {"Content-Type": "application/json"}


def test_format_judge_response_extracts_llm_answer() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"accuracy": 5}',
                }
            }
        ]
    }

    assert format_judge_response(response) == {"llm_answer": '{"accuracy": 5}'}


def test_format_judge_response_rejects_invalid_payload() -> None:
    with pytest.raises(EvaluatorClientError):
        format_judge_response({"choices": []})
