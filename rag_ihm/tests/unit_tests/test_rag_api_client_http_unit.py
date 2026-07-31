from datetime import date

import pytest

from app.services import rag_api_client as client
from app.services.rag_api_client import ChatApiConfig, RagApiError


class FakeResponse:
    def __init__(self, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self.payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


def test_ask_question_requires_access_token() -> None:
    with pytest.raises(RagApiError, match="session a expiré"):
        client.ask_question(
            ChatApiConfig("http://health", "http://rag/ask_question"),
            "?",
            "local",
            None,
        )


def test_ask_question_posts_streamlit_channel_and_bearer_token(monkeypatch) -> None:
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        return FakeResponse(payload={"llm_response": "ok"})

    monkeypatch.setattr(client.requests, "post", fake_post)

    result = client.ask_question(
        ChatApiConfig("http://health", "http://rag/ask_question"),
        "Question",
        "api",
        "token",
    )

    assert result == {"llm_response": "ok"}
    assert calls == [
        {
            "url": "http://rag/ask_question",
            "json": {"question": "Question", "provider": "api", "channel": "streamlit"},
            "headers": {"Authorization": "Bearer token"},
            "timeout": 360,
        }
    ]


def test_admin_feedbacks_request_sends_iso_dates_and_expects_a_list(
    monkeypatch,
) -> None:
    calls = []

    def fake_request(method, url, params, json, headers, timeout):
        calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse(payload=[])

    monkeypatch.setattr(client.requests, "request", fake_request)

    result = client.list_admin_interaction_feedbacks(
        ChatApiConfig("http://health", "http://rag/ask_question"),
        "token",
        date(2026, 1, 1),
        date(2026, 1, 31),
    )

    assert result == []
    assert calls[0]["url"] == "http://rag/usage/admin/interactions/feedbacks"
    assert calls[0]["params"] == {"start_date": "2026-01-01", "end_date": "2026-01-31"}
    assert calls[0]["headers"] == {"Authorization": "Bearer token"}


def test_response_json_rejects_non_dict_payload() -> None:
    with pytest.raises(RagApiError, match="format inattendu"):
        client._response_json(FakeResponse(payload=[]))
