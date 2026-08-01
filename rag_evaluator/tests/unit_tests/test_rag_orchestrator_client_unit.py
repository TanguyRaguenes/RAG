from pathlib import Path
from runpy import run_path
from typing import ClassVar, Self

import httpx
import pytest

from app.core.exceptions import (
    EvaluatorAuthenticationError,
    EvaluatorAuthorizationError,
    EvaluatorClientError,
)
from app.dal.clients import rag_orchestrator_client as client
from app.dal.clients.rag_orchestrator_client import (
    HttpRagOrchestratorClient,
    derive_auth_me_url,
)
from app.schemas.orchestrator_schema import AskQuestionRequest


def _valid_response() -> dict[str, object]:
    return {
        "llm_response": "ok",
        "retrieved_chunks": [
            {"document": "doc", "metadata": {"title": "Doc"}, "similarity": 0.9}
        ],
        "retrieved_documents": {"Doc": 1},
        "model": "model",
        "generated_prompt": [],
        "duration": "00:01",
    }


def _valid_user() -> dict[str, object]:
    return {
        "issuer": "https://identity.example",
        "sub": "user-1",
        "email": "admin@example.test",
        "groups": ["rag_admin"],
    }


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code
        self.request = httpx.Request("GET", "http://orchestrator/auth/me")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("failed", request=self.request, response=self)

    def json(self) -> object:
        return self.payload


class FakeAsyncClient:
    calls: ClassVar[list[dict[str, object]]] = []
    responses: ClassVar[list[FakeResponse]] = []

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False

    async def request(self, method: str, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(
            {"method": method, "url": url, "timeout": self.timeout, **kwargs}
        )
        return self.responses.pop(0)


def test_derive_auth_url_preserves_deployment_prefix() -> None:
    assert (
        derive_auth_me_url(
            "https://rag.example/api/v1/ask_question?debug=true#fragment"
        )
        == "https://rag.example/api/v1/auth/me"
    )
    assert derive_auth_me_url("http://orchestrator/ask_question/") == (
        "http://orchestrator/auth/me"
    )


@pytest.mark.asyncio
async def test_client_verifies_identity_and_propagates_same_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [
        FakeResponse(_valid_user()),
        FakeResponse(_valid_response()),
    ]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)
    orchestrator = HttpRagOrchestratorClient("http://orchestrator/ask_question")

    user = await orchestrator.get_current_user("opaque-token")
    result = await orchestrator.ask_question("Question", "opaque-token")

    assert user.groups == ["rag_admin"]
    assert result.llm_response == "ok"
    assert FakeAsyncClient.calls == [
        {
            "method": "GET",
            "url": "http://orchestrator/auth/me",
            "headers": {"Authorization": "Bearer opaque-token"},
            "timeout": 180.0,
        },
        {
            "method": "POST",
            "url": "http://orchestrator/ask_question",
            "headers": {"Authorization": "Bearer opaque-token"},
            "json": {
                "question": "Question",
                "provider": "api",
                "channel": "api",
            },
            "timeout": 180.0,
        },
    ]


@pytest.mark.asyncio
async def test_client_uses_dedicated_auth_url_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [FakeResponse(_valid_user())]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setenv(
        "RAG_ORCHESTRATOR_ASK_QUESTION_URL",
        "http://orchestrator/api/ask_question",
    )
    monkeypatch.setenv(
        "RAG_ORCHESTRATOR_AUTH_ME_URL",
        "http://identity-proxy/orchestrator/auth/me",
    )

    await HttpRagOrchestratorClient.from_environment().get_current_user("token")

    assert FakeAsyncClient.calls[0]["url"] == (
        "http://identity-proxy/orchestrator/auth/me"
    )


@pytest.mark.asyncio
async def test_client_sends_configured_local_rag_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [FakeResponse(_valid_response())]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    await HttpRagOrchestratorClient(
        "http://orchestrator/ask_question",
        rag_provider="local",
    ).ask_question("Question", "token")

    assert FakeAsyncClient.calls[0]["json"] == {
        "question": "Question",
        "provider": "local",
        "channel": "api",
    }


@pytest.mark.asyncio
async def test_client_maps_upstream_unauthorized_to_authentication_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.responses = [FakeResponse({}, status_code=401)]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorAuthenticationError):
        await HttpRagOrchestratorClient(
            "http://orchestrator/ask_question"
        ).get_current_user("expired-token")


@pytest.mark.asyncio
async def test_client_maps_auth_me_forbidden_to_authorization_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.responses = [FakeResponse({}, status_code=403)]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorAuthorizationError):
        await HttpRagOrchestratorClient(
            "http://orchestrator/ask_question"
        ).get_current_user("token")


@pytest.mark.asyncio
async def test_client_maps_ask_question_forbidden_to_authorization_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.responses = [FakeResponse({}, status_code=403)]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorAuthorizationError) as error:
        await HttpRagOrchestratorClient(
            "http://orchestrator/ask_question"
        ).ask_question("Question", "token")

    assert error.value.details == {}
    assert error.value.internal_details == {
        "operation": "ask_question",
        "upstream_status": 403,
    }


@pytest.mark.asyncio
async def test_client_rejects_incomplete_external_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeAsyncClient.responses = [FakeResponse({"llm_response": "incomplete"})]
    monkeypatch.setattr(client.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(EvaluatorClientError, match="réponse invalide"):
        await HttpRagOrchestratorClient(
            "http://orchestrator/ask_question"
        ).ask_question("Question", "token")


def test_client_requires_configured_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL", raising=False)

    with pytest.raises(EvaluatorClientError):
        HttpRagOrchestratorClient.from_environment()


def test_evaluator_request_matches_orchestrator_input_contract() -> None:
    orchestrator_schema_path = (
        Path(__file__).parents[3]
        / "rag_orchestrator"
        / "app"
        / "schemas"
        / "ask_question_request_schema.py"
    )
    orchestrator_request_model = run_path(orchestrator_schema_path)[
        "AskQuestionRequestBase"
    ]
    payload = AskQuestionRequest(
        question="Question",
        provider="api",
        channel="api",
    ).model_dump()

    validated_request = orchestrator_request_model.model_validate(payload)

    assert validated_request.model_dump() == payload
