import pytest
from fastapi import HTTPException

from app.api.routers import query_router
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase
from app.services.usage_tracking_service import QuotaExceededError


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(sub="user-1", email="user@example.com")


def _config() -> dict:
    return {
        "llm": {
            "local": {"provider": "local-provider"},
            "api": {"provider": "api-provider"},
        }
    }


@pytest.mark.asyncio
async def test_ask_question_route_success_saves_usage_and_finishes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_start_usage_session(user, db_pool, channel):
        calls.append(("start", user.sub, channel))
        return "hashed-user", 42

    async def fake_check_user_token_quota(db_pool, user_id):
        calls.append(("quota", user_id))

    async def fake_ask_question_to_local_model(question, config):
        calls.append(("rag", question))
        return AskQuestionResponseBase(
            llm_response="answer",
            retrieved_chunks=[],
            retrieved_documents={},
            model="model",
            generated_prompt=[],
            duration="",
        )

    async def fake_save_successful_question_usage(**kwargs):
        calls.append(("success", kwargs["session_id"], kwargs["llm_provider"]))
        return 99

    async def fake_finish_usage_session(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(query_router, "start_usage_session", fake_start_usage_session)
    monkeypatch.setattr(
        query_router, "check_user_token_quota", fake_check_user_token_quota
    )
    monkeypatch.setattr(
        query_router, "ask_question_to_local_model", fake_ask_question_to_local_model
    )
    monkeypatch.setattr(
        query_router,
        "save_successful_question_usage",
        fake_save_successful_question_usage,
    )
    monkeypatch.setattr(query_router, "finish_usage_session", fake_finish_usage_session)
    monkeypatch.setattr(query_router.time, "perf_counter", iter([1.0, 2.0]).__next__)

    response = await query_router.ask_question_route(
        AskQuestionRequestBase(question="Q", provider="local", channel="streamlit"),
        _user(),
        _config(),
        db_pool=object(),
    )

    assert response.interaction_id == 99
    assert response.duration == "00:01"
    assert calls == [
        ("start", "user-1", "streamlit"),
        ("quota", "hashed-user"),
        ("rag", "Q"),
        ("success", 42, "local-provider"),
        ("finish", 42),
    ]


@pytest.mark.asyncio
async def test_ask_question_route_saves_failure_when_quota_is_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_start_usage_session(user, db_pool, channel):
        return "hashed-user", 42

    async def fake_check_user_token_quota(db_pool, user_id):
        raise QuotaExceededError(100, 100)

    async def fake_save_failed_question_usage(**kwargs):
        calls.append(("failed", kwargs["status"], kwargs["session_id"]))

    async def fake_finish_usage_session(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(query_router, "start_usage_session", fake_start_usage_session)
    monkeypatch.setattr(
        query_router, "check_user_token_quota", fake_check_user_token_quota
    )
    monkeypatch.setattr(
        query_router, "save_failed_question_usage", fake_save_failed_question_usage
    )
    monkeypatch.setattr(query_router, "finish_usage_session", fake_finish_usage_session)
    monkeypatch.setattr(query_router.time, "perf_counter", lambda: 1.0)

    with pytest.raises(HTTPException) as exc_info:
        await query_router.ask_question_route(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
            _config(),
            db_pool=object(),
        )

    assert exc_info.value.status_code == 403
    assert calls == [("failed", "quota_exceeded", 42), ("finish", 42)]


@pytest.mark.asyncio
async def test_retrieve_chunks_route_saves_retrieval_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def fake_start_usage_session(user, db_pool, channel):
        calls.append(("start", channel))
        return "hashed-user", 7

    async def fake_retrieve_chunks(question, config):
        calls.append(("retrieve", question))
        return RetrieveChunksResponseBase(retrieved_chunks=[{"document": "doc"}])

    async def fake_save_retrieval_usage(**kwargs):
        calls.append(("usage", kwargs["session_id"], kwargs["retrieved_chunks"]))

    async def fake_finish_usage_session(db_pool, session_id):
        calls.append(("finish", session_id))

    monkeypatch.setattr(query_router, "start_usage_session", fake_start_usage_session)
    monkeypatch.setattr(query_router, "retrieve_chunks", fake_retrieve_chunks)
    monkeypatch.setattr(query_router, "save_retrieval_usage", fake_save_retrieval_usage)
    monkeypatch.setattr(query_router, "finish_usage_session", fake_finish_usage_session)
    monkeypatch.setattr(query_router.time, "perf_counter", iter([1.0, 1.5]).__next__)

    response = await query_router.retrieve_chunks_route(
        RetrieveChunksRequestBase(question="Q"),
        _user(),
        _config(),
        db_pool=object(),
    )

    assert response.retrieved_chunks == [{"document": "doc"}]
    assert calls == [
        ("start", "mcp"),
        ("retrieve", "Q"),
        ("usage", 7, [{"document": "doc"}]),
        ("finish", 7),
    ]
