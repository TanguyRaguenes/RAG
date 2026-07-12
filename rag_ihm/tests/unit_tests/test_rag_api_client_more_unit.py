import pytest

from app.services import rag_api_client as client
from app.services.rag_api_client import ChatApiConfig, EvaluatorApiConfig, RagApiError


class FakeResponse:
    def __init__(self, status_code: int = 200, payload=None, text: str = ""):
        self.status_code = status_code
        self.payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        if isinstance(self.payload, BaseException):
            raise self.payload
        return self.payload


def test_load_api_configs_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ORCHESTRATOR_TEST_CONNEXION_URL", "http://rag")
    monkeypatch.setenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL", "http://rag/ask_question")
    monkeypatch.setenv("RAG_EVALUATOR_TEST_CONNEXION_URL", "http://eval")
    monkeypatch.setenv("RAG_EVALUATOR_EVALUATE_RAG_URL", "http://eval/evaluate_rag")

    assert client.load_chat_api_config().ask_question_url == "http://rag/ask_question"
    assert client.load_evaluator_api_config().evaluate_url == "http://eval/evaluate_rag"


def test_check_api_health_raises_displayable_error_for_non_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        client.requests,
        "get",
        lambda url, timeout: FakeResponse(503, {"detail": "down"}),
    )

    with pytest.raises(RagApiError, match="503"):
        client.check_api_health("http://service")


def test_quota_preferences_and_feedback_endpoints_use_authenticated_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    payloads = iter(
        [
            {"quota": True},
            [{"user": "u"}],
            {"updated": True},
            {"theme_preference": "Sombre"},
            {"theme_preference": "Clair"},
            {"feedback": True},
        ]
    )

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
        return FakeResponse(payload=next(payloads))

    monkeypatch.setattr(client.requests, "request", fake_request)
    config = ChatApiConfig("http://health", "http://rag/ask_question")

    assert client.get_my_quota_usage(config, "token") == {"quota": True}
    assert client.list_admin_quota_usages(config, "token") == [{"user": "u"}]
    assert client.update_admin_quota_usage(config, "token", "user", 100, True) == {
        "updated": True
    }
    assert client.get_my_preferences(config, "token") == {"theme_preference": "Sombre"}
    assert client.update_my_preferences(config, "token", "Clair") == {
        "theme_preference": "Clair"
    }
    assert client.submit_interaction_feedback(config, "token", 1, 1, "ok") == {
        "feedback": True
    }

    assert calls[2]["method"] == "PATCH"
    assert calls[2]["json"] == {"max_tokens_par_mois": 100, "actif": True}
    assert calls[-1]["json"] == {"note": 1, "commentaire": "ok"}


def test_run_evaluation_posts_to_evaluator(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_post(url, timeout):
        calls.append({"url": url, "timeout": timeout})
        return FakeResponse(payload={"total_questions": 1})

    monkeypatch.setattr(client.requests, "post", fake_post)

    assert client.run_evaluation(
        EvaluatorApiConfig("http://health", "http://eval/evaluate")
    ) == {"total_questions": 1}
    assert calls == [{"url": "http://eval/evaluate", "timeout": 300}]


def test_authenticated_request_wraps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_request(*args, **kwargs):
        raise client.requests.exceptions.Timeout("slow")

    monkeypatch.setattr(client.requests, "request", failing_request)

    with pytest.raises(RagApiError, match="trop de temps"):
        client._authenticated_request("GET", "http://rag", "token")
