import pytest
from app.core.exceptions import (
    QuestionQuotaExceededError,
    QuotaExceededError,
    QuotaInactiveError,
)
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase
from app.services import question_orchestration_service as orchestration_module
from app.services.question_orchestration_service import (
    QuestionOrchestrationService,
)


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(issuer="issuer", sub="User-1")


def _config() -> dict:
    return {
        "llm": {
            "local": {"provider": "local-provider"},
            "api": {"provider": "api-provider"},
        }
    }


def _disable_observability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        orchestration_module,
        "record_orchestration_success",
        lambda *args: None,
    )
    monkeypatch.setattr(
        orchestration_module,
        "record_orchestration_error",
        lambda *args: None,
    )


@pytest.mark.asyncio
async def test_ask_question_orchestration_saves_usage_and_finishes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    _disable_observability(monkeypatch)

    async def fake_start(user, db_pool, channel):
        calls.append(("start", user.sub, channel))
        return "hashed-user", 42

    async def fake_quota(db_pool, user_id):
        calls.append(("quota", user_id))

    async def fake_ask(question, config):
        calls.append(("rag", question))
        return AskQuestionResponseBase(
            llm_response="answer",
            retrieved_chunks=[],
            retrieved_documents={},
            model="model",
            generated_prompt=[],
            duration="",
        )

    async def fake_save_success(**kwargs):
        calls.append(("success", kwargs["session_id"], kwargs["llm_provider"]))
        return 99

    async def fake_finish(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(orchestration_module, "start_usage_session", fake_start)
    monkeypatch.setattr(orchestration_module, "check_user_token_quota", fake_quota)
    monkeypatch.setattr(orchestration_module, "ask_question_to_local_model", fake_ask)
    monkeypatch.setattr(
        orchestration_module,
        "save_successful_question_usage",
        fake_save_success,
    )
    monkeypatch.setattr(orchestration_module, "finish_usage_session", fake_finish)
    monkeypatch.setattr(
        orchestration_module.time,
        "perf_counter",
        iter([1.0, 2.0]).__next__,
    )

    response = await QuestionOrchestrationService(_config(), object()).ask_question(
        AskQuestionRequestBase(question="Q", provider="local", channel="streamlit"),
        _user(),
    )

    assert response.interaction_id == 99
    assert response.duration == "00:01"
    assert calls == [
        ("start", "User-1", "streamlit"),
        ("quota", "hashed-user"),
        ("rag", "Q"),
        ("success", 42, "local-provider"),
        ("finish", 42),
    ]


@pytest.mark.asyncio
async def test_quota_exceeded_is_saved_and_session_is_finished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    _disable_observability(monkeypatch)

    async def fake_start(user, db_pool, channel):
        return "hashed-user", 42

    async def fake_quota(db_pool, user_id):
        raise QuotaExceededError(100, 100)

    async def fake_save_failed(**kwargs):
        calls.append(("failed", kwargs["status"], kwargs["session_id"]))

    async def fake_finish(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(orchestration_module, "start_usage_session", fake_start)
    monkeypatch.setattr(orchestration_module, "check_user_token_quota", fake_quota)
    monkeypatch.setattr(
        orchestration_module,
        "save_failed_question_usage",
        fake_save_failed,
    )
    monkeypatch.setattr(orchestration_module, "finish_usage_session", fake_finish)
    monkeypatch.setattr(orchestration_module.time, "perf_counter", lambda: 1.0)

    with pytest.raises(QuestionQuotaExceededError):
        await QuestionOrchestrationService(_config(), object()).ask_question(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
        )

    assert calls == [("failed", "quota_exceeded", 42), ("finish", 42)]


@pytest.mark.asyncio
async def test_inactive_quota_uses_same_business_error_and_finishes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    _disable_observability(monkeypatch)

    async def fake_start(user, db_pool, channel):
        return "hashed-user", 42

    async def fake_quota(db_pool, user_id):
        raise QuotaInactiveError()

    async def fake_save_failed(**kwargs):
        calls.append(("failed", kwargs["status"], kwargs["session_id"]))

    async def fake_finish(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(orchestration_module, "start_usage_session", fake_start)
    monkeypatch.setattr(orchestration_module, "check_user_token_quota", fake_quota)
    monkeypatch.setattr(
        orchestration_module,
        "save_failed_question_usage",
        fake_save_failed,
    )
    monkeypatch.setattr(orchestration_module, "finish_usage_session", fake_finish)
    monkeypatch.setattr(orchestration_module.time, "perf_counter", lambda: 1.0)

    with pytest.raises(QuestionQuotaExceededError):
        await QuestionOrchestrationService(_config(), object()).ask_question(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
        )

    assert calls == [("failed", "quota_exceeded", 42), ("finish", 42)]


@pytest.mark.asyncio
async def test_unexpected_quota_error_still_finishes_started_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    _disable_observability(monkeypatch)

    async def fake_start(user, db_pool, channel):
        return "hashed-user", 42

    async def fake_quota(db_pool, user_id):
        raise RuntimeError("database unavailable")

    async def fake_save_failed(**kwargs):
        calls.append(("failed", kwargs["status"]))

    async def fake_finish(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(orchestration_module, "start_usage_session", fake_start)
    monkeypatch.setattr(orchestration_module, "check_user_token_quota", fake_quota)
    monkeypatch.setattr(
        orchestration_module,
        "save_failed_question_usage",
        fake_save_failed,
    )
    monkeypatch.setattr(orchestration_module, "finish_usage_session", fake_finish)
    monkeypatch.setattr(orchestration_module.time, "perf_counter", lambda: 1.0)

    with pytest.raises(RuntimeError, match="database unavailable"):
        await QuestionOrchestrationService(_config(), object()).ask_question(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
        )

    assert calls == [("failed", "error"), ("finish", 42)]


@pytest.mark.asyncio
async def test_retrieve_chunks_orchestration_persists_and_finishes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    _disable_observability(monkeypatch)

    async def fake_start(user, db_pool, channel):
        calls.append(("start", channel))
        return "hashed-user", 7

    async def fake_retrieve(question, config):
        calls.append(("retrieve", question))
        return RetrieveChunksResponseBase(retrieved_chunks=[{"document": "doc"}])

    async def fake_save(**kwargs):
        calls.append(("usage", kwargs["session_id"]))

    async def fake_finish(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(orchestration_module, "start_usage_session", fake_start)
    monkeypatch.setattr(orchestration_module, "retrieve_chunks", fake_retrieve)
    monkeypatch.setattr(orchestration_module, "save_retrieval_usage", fake_save)
    monkeypatch.setattr(orchestration_module, "finish_usage_session", fake_finish)
    monkeypatch.setattr(
        orchestration_module.time,
        "perf_counter",
        iter([1.0, 1.5]).__next__,
    )

    response = await QuestionOrchestrationService(_config(), object()).retrieve_chunks(
        RetrieveChunksRequestBase(question="Q"),
        _user(),
    )

    assert response.retrieved_chunks == [{"document": "doc"}]
    assert calls == [
        ("start", "mcp"),
        ("retrieve", "Q"),
        ("usage", 7),
        ("finish", 7),
    ]
