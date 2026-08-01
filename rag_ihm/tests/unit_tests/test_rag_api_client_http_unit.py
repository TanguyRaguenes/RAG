from datetime import date
from typing import Any

import pytest

from app.core.errors import RagApiError
from app.dal.clients import http_client
from app.dal.clients.http_client import RequestsHttpClient
from app.dal.clients.oidc_client import OidcClient
from app.services import rag_api_client as service
from app.services.rag_api_client import ChatApiConfig


class FakeRagClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def request_json(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.payload


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: object = None) -> None:
        self.status_code = status_code
        self.payload = {} if payload is None else payload

    def json(self) -> object:
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


def _ask_question_response() -> dict[str, object]:
    return {
        "interaction_id": None,
        "llm_response": "ok",
        "retrieved_documents": {},
        "retrieved_chunks": [],
        "model": "model",
        "duration": "00:01",
        "input_tokens": 1,
        "output_tokens": 2,
        "total_tokens": 3,
        "cost": 0.01,
        "generated_prompt": [],
    }


def test_ask_question_requires_access_token() -> None:
    with pytest.raises(RagApiError, match="session a expiré"):
        service.ask_question(
            ChatApiConfig("http://health", "http://rag/ask_question"),
            "?",
            "local",
            None,
        )


def test_ask_question_posts_streamlit_channel_and_bearer_token() -> None:
    payload = _ask_question_response()
    client = FakeRagClient(payload)

    result = service.ask_question(
        ChatApiConfig("http://health", "http://rag/ask_question"),
        "Question",
        "api",
        "token",
        client,
    )

    assert result == payload
    assert client.calls[0]["payload"] == {
        "question": "Question",
        "provider": "api",
        "channel": "streamlit",
    }
    assert client.calls[0]["access_token"] == "token"
    assert client.calls[0]["timeout"] == 360


def test_admin_feedbacks_request_sends_iso_dates_and_expects_a_list() -> None:
    client = FakeRagClient([])

    result = service.list_admin_interaction_feedbacks(
        ChatApiConfig("http://health", "http://rag/ask_question"),
        "token",
        date(2026, 1, 1),
        date(2026, 1, 31),
        client,
    )

    assert result == []
    assert client.calls[0]["url"] == "http://rag/usage/admin/interactions/feedbacks"
    assert client.calls[0]["params"] == {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }


def test_response_boundary_rejects_non_dict_payload() -> None:
    with pytest.raises(RagApiError, match="réponse invalide"):
        service.ask_question(
            ChatApiConfig("http://health", "http://rag/ask_question"),
            "Question",
            "api",
            "token",
            FakeRagClient([]),
        )


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("model", None),
        ("total_tokens", True),
        ("retrieved_chunks", {}),
        ("generated_prompt", ["invalid"]),
    ],
)
def test_ask_question_rejects_missing_or_invalid_contract_fields(
    field: str,
    invalid_value: object,
) -> None:
    payload = _ask_question_response()
    payload[field] = invalid_value

    with pytest.raises(RagApiError, match="réponse invalide"):
        service.ask_question(
            ChatApiConfig("http://health", "http://rag/ask_question"),
            "Question",
            "api",
            "token",
            FakeRagClient(payload),
        )


def test_ask_question_accepts_missing_optional_interaction_id() -> None:
    payload = _ask_question_response()
    del payload["interaction_id"]

    result = service.ask_question(
        ChatApiConfig("http://health", "http://rag/ask_question"),
        "Question",
        "api",
        "token",
        FakeRagClient(payload),
    )

    assert "interaction_id" not in result


def test_http_client_never_exposes_backend_response_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(status_code=503, payload={"detail": "secret backend"})
    monkeypatch.setattr(
        http_client.requests, "request", lambda *args, **kwargs: response
    )

    with pytest.raises(RagApiError) as raised:
        RequestsHttpClient().request_json("GET", "http://rag", timeout=5)

    assert raised.value.details == {"status_code": 503}
    assert "secret backend" not in raised.value.user_message


def test_oidc_client_rejects_malformed_token_response() -> None:
    client = FakeRagClient({"access_token": 123, "refresh_token": "secret"})

    with pytest.raises(RagApiError) as raised:
        OidcClient(client).exchange_code(
            token_url="http://token",
            client_id="client",
            client_secret="secret",
            code="secret-code",
            redirect_uri="http://redirect",
        )

    assert raised.value.code == "oidc_response_contract_error"
    assert "secret-code" not in str(raised.value)
