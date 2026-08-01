import pytest
from app.api.routers import query_router
from app.core.exceptions import QuestionQuotaExceededError, UsageSessionValidationError
from app.schemas.ask_question_request_schema import AskQuestionRequestBase
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.authenticated_user_schema import AuthenticatedUser
from app.schemas.retrieve_chunks_request_schema import RetrieveChunksRequestBase
from app.schemas.retrieve_chunks_response_schema import RetrieveChunksResponseBase


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(issuer="issuer", sub="user-1", email="user@example.com")


class FakeQuestionOrchestrationService:
    def __init__(self) -> None:
        self.ask_error: Exception | None = None
        self.retrieve_error: Exception | None = None

    async def ask_question(
        self,
        body: AskQuestionRequestBase,
        current_user: AuthenticatedUser,
    ) -> AskQuestionResponseBase:
        if self.ask_error:
            raise self.ask_error
        assert body.question == "Q"
        assert current_user.sub == "user-1"
        return AskQuestionResponseBase(
            llm_response="answer",
            retrieved_chunks=[],
            retrieved_documents={},
            model="model",
            generated_prompt=[],
            duration="00:01",
        )

    async def retrieve_chunks(
        self,
        body: RetrieveChunksRequestBase,
        current_user: AuthenticatedUser,
    ) -> RetrieveChunksResponseBase:
        if self.retrieve_error:
            raise self.retrieve_error
        assert body.question == "Q"
        assert current_user.sub == "user-1"
        return RetrieveChunksResponseBase(retrieved_chunks=[{"document": "doc"}])


@pytest.mark.asyncio
async def test_ask_question_route_delegates_to_injected_service() -> None:
    response = await query_router.ask_question_route(
        AskQuestionRequestBase(question="Q", provider="local", channel="streamlit"),
        _user(),
        FakeQuestionOrchestrationService(),
    )

    assert response.llm_response == "answer"
    assert response.duration == "00:01"


@pytest.mark.asyncio
async def test_ask_question_route_propagates_application_errors_to_handler() -> None:
    service = FakeQuestionOrchestrationService()
    service.ask_error = QuestionQuotaExceededError()

    with pytest.raises(QuestionQuotaExceededError):
        await query_router.ask_question_route(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
            service,
        )

    service.ask_error = UsageSessionValidationError("invalid session")
    with pytest.raises(UsageSessionValidationError):
        await query_router.ask_question_route(
            AskQuestionRequestBase(question="Q", provider="local"),
            _user(),
            service,
        )


@pytest.mark.asyncio
async def test_retrieve_chunks_route_delegates_to_injected_service() -> None:
    response = await query_router.retrieve_chunks_route(
        RetrieveChunksRequestBase(question="Q"),
        _user(),
        FakeQuestionOrchestrationService(),
    )

    assert response.retrieved_chunks == [{"document": "doc"}]
