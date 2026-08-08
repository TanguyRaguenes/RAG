from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest

from app.core.errors import RagApiError
from app.services import rag_api_client as service
from app.services.rag_api_client import ChatApiConfig, EvaluatorApiConfig


class FakeRagClient:
    def __init__(self, payloads: list[object] | None = None) -> None:
        self._payloads: Iterator[object] = iter(payloads or [])
        self.calls: list[dict[str, Any]] = []
        self.health_urls: list[str] = []

    def check_health(self, url: str) -> None:
        self.health_urls.append(url)

    def request_json(self, method: str, url: str, **kwargs: object) -> object:
        self.calls.append({"method": method, "url": url, **kwargs})
        return next(self._payloads)


def _evaluation_response() -> dict[str, object]:
    return {
        "average_retrieval": {
            "mrr": 1.0,
            "ndcg": 0.9,
            "recall": 0.8,
            "precision": 0.7,
            "source_hit_at_5": 1.0,
        },
        "average_answer_quality": {
            "feedback": "ok",
            "accuracy": 5.0,
            "completeness": 4.0,
            "relevance": 5.0,
            "faithfulness": 4.0,
            "safe_refusal": 3.0,
        },
        "total_duration": "00:01",
        "total_questions": 1,
    }


def _quota_response() -> dict[str, object]:
    return {
        "utilisateur_id": "user-id",
        "email": None,
        "display_name": "User",
        "preferred_username": None,
        "max_tokens_par_mois": 100,
        "consumed_tokens": 10,
        "remaining_tokens": 90,
        "usage_ratio": 0.1,
        "actif": True,
        "illimite": False,
        "date_debut": "2026-08-01T00:00:00Z",
        "date_fin": None,
    }


def _feedback_response() -> dict[str, object]:
    return {"interaction_id": 1, "note": 1, "commentaire": "ok"}


def test_load_api_configs_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_ORCHESTRATOR_TEST_CONNEXION_URL", "http://rag/health")
    monkeypatch.setenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL", "http://rag/ask_question")
    monkeypatch.setenv("RAG_EVALUATOR_TEST_CONNEXION_URL", "http://eval/health")
    monkeypatch.setenv("RAG_EVALUATOR_EVALUATE_RAG_URL", "http://eval/evaluate_rag")

    assert service.load_chat_api_config().ask_question_url == "http://rag/ask_question"
    assert (
        service.load_evaluator_api_config().evaluate_url == "http://eval/evaluate_rag"
    )


def test_check_api_health_uses_configured_url_unchanged() -> None:
    client = FakeRagClient()

    service.check_api_health("http://service/health", client=client)

    assert client.health_urls == ["http://service/health"]


def test_quota_and_feedback_endpoints_use_injected_client() -> None:
    client = FakeRagClient(
        [
            _quota_response(),
            [_quota_response()],
            _quota_response(),
            _feedback_response(),
        ]
    )
    config = ChatApiConfig("http://health", "http://rag/ask_question")

    assert service.get_my_quota_usage(config, "token", client) == _quota_response()
    assert service.list_admin_quota_usages(config, "token", client) == [
        _quota_response()
    ]
    assert (
        service.update_admin_quota_usage(
            config, "token", "user", 100, True, True, client
        )
        == _quota_response()
    )
    assert service.submit_interaction_feedback(config, "token", 1, 1, "ok", client) == {
        "interaction_id": 1,
        "note": 1,
        "commentaire": "ok",
    }

    assert client.calls[2]["method"] == "PATCH"
    assert client.calls[2]["payload"] == {
        "max_tokens_par_mois": 100,
        "actif": True,
        "illimite": True,
    }
    assert client.calls[-1]["payload"] == {"note": 1, "commentaire": "ok"}


def test_run_evaluation_propagates_user_identity() -> None:
    payload = _evaluation_response()
    client = FakeRagClient([payload])

    result = service.run_evaluation(
        EvaluatorApiConfig("http://health", "http://eval/evaluate"),
        "user-token",
        client,
    )

    assert result == payload
    assert client.calls == [
        {
            "method": "POST",
            "url": "http://eval/evaluate",
            "timeout": None,
            "access_token": "user-token",
            "params": None,
            "payload": None,
        }
    ]


def test_run_evaluation_sends_selected_question_limit() -> None:
    payload = _evaluation_response()
    client = FakeRagClient([payload])

    result = service.run_evaluation(
        EvaluatorApiConfig("http://health", "http://eval/evaluate"),
        "user-token",
        client,
        question_limit=25,
    )

    assert result == payload
    assert client.calls[0]["payload"] == {"question_limit": 25}


@pytest.mark.parametrize(
    "payload",
    [
        {"total_questions": 1},
        {**_evaluation_response(), "total_questions": True},
        {**_evaluation_response(), "average_retrieval": {}},
        {
            **_evaluation_response(),
            "average_answer_quality": {
                **_evaluation_response()["average_answer_quality"],
                "accuracy": "5",
            },
        },
    ],
)
def test_run_evaluation_rejects_incomplete_or_invalid_contract(
    payload: dict[str, object],
) -> None:
    with pytest.raises(RagApiError, match="réponse invalide"):
        service.run_evaluation(
            EvaluatorApiConfig("http://health", "http://eval/evaluate"),
            "user-token",
            FakeRagClient([payload]),
        )


def test_authenticated_request_requires_token() -> None:
    with pytest.raises(RagApiError, match="session a expiré"):
        service._authenticated_request(
            "GET", "http://rag", None, client=FakeRagClient()
        )


@pytest.mark.parametrize(
    ("operation", "payload"),
    [
        ("my_quota", {**_quota_response(), "usage_ratio": "0.1"}),
        ("quota_list", [{**_quota_response(), "actif": 1}]),
        ("quota_update", {**_quota_response(), "consumed_tokens": True}),
        ("feedback", {**_feedback_response(), "note": 0}),
        (
            "admin_feedbacks",
            [
                {
                    "interaction_id": 1,
                    "cree_le": "2026-08-01T00:00:00Z",
                    "question": "private question",
                    "reponse": None,
                    "note": 1,
                    "commentaire": None,
                    "chunks": [{"rang": "first"}],
                }
            ],
        ),
    ],
)
def test_quota_and_feedback_operations_reject_malformed_contracts(
    operation: str,
    payload: object,
) -> None:
    config = ChatApiConfig("http://health", "http://rag/ask_question")
    client = FakeRagClient([payload])

    with pytest.raises(RagApiError) as raised:
        if operation == "my_quota":
            service.get_my_quota_usage(config, "token", client)
        elif operation == "quota_list":
            service.list_admin_quota_usages(config, "token", client)
        elif operation == "quota_update":
            service.update_admin_quota_usage(
                config, "token", "user-id", 100, True, False, client
            )
        elif operation == "feedback":
            service.submit_interaction_feedback(
                config, "token", 1, 1, "private comment", client
            )
        else:
            service.list_admin_interaction_feedbacks(
                config,
                "token",
                date(2026, 8, 1),
                date(2026, 8, 2),
                client,
            )

    assert raised.value.code == "response_contract_error"
    assert "private comment" not in str(raised.value)
