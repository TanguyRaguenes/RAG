import json
from pathlib import Path

import pytest

from app.core.config import EvaluatorConfig
from app.core.exceptions import (
    DatasetException,
    EvaluatorAuthorizationError,
    EvaluatorClientError,
)
from app.dal.clients.dataset_repository import JsonDatasetRepository
from app.schemas.answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.dataset_schema import EvaluationCase
from app.schemas.judge_schema import JudgeMessage
from app.schemas.orchestrator_schema import AskQuestionResponse, AuthenticatedUser
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services import evaluating_service
from app.services.evaluating_service import (
    EvaluationService,
    add_quality_score,
    add_retrieval_score,
    build_empty_evaluation_response,
    build_quality_accumulator,
    build_retrieval_accumulator,
    calculate_average_quality,
    calculate_average_retrieval,
)


def _config() -> EvaluatorConfig:
    return EvaluatorConfig.model_validate(
        {
            "llm": {
                "provider": "ollama",
                "url_provider": "http://ollama",
                "model": "judge",
                "temperature": 0.1,
                "num_ctx": 1024,
                "max_output_token": 128,
                "timeout_seconds": 10,
            },
            "evaluation_method": {"use_api_openai": False},
        }
    )


class FakeDatasetRepository:
    def __init__(self, cases: list[EvaluationCase]) -> None:
        self.cases = cases

    def load(self) -> list[EvaluationCase]:
        return self.cases


class FakeOrchestratorClient:
    def __init__(
        self,
        error: Exception | None = None,
        groups: list[str] | None = None,
    ) -> None:
        self.error = error
        self.groups = groups or ["rag_admin"]
        self.auth_tokens: list[str] = []
        self.question_calls: list[tuple[str, str]] = []

    async def get_current_user(self, access_token: str) -> AuthenticatedUser:
        self.auth_tokens.append(access_token)
        return AuthenticatedUser(
            issuer="https://identity.example",
            sub="user-1",
            groups=self.groups,
        )

    async def ask_question(
        self, question: str, access_token: str
    ) -> AskQuestionResponse:
        self.question_calls.append((question, access_token))
        if self.error:
            raise self.error
        return AskQuestionResponse.model_validate(
            {
                "llm_response": f"answer {question}",
                "retrieved_chunks": [
                    {
                        "document": "doc keyword",
                        "metadata": {"title": "Doc"},
                        "similarity": 0.9,
                    }
                ],
                "retrieved_documents": {"Doc": 1},
                "model": "model",
                "generated_prompt": [],
                "duration": "00:01",
            }
        )


class UnusedJudgeClient:
    async def judge(self, messages: list[JudgeMessage]) -> str:
        raise AssertionError("evaluate_answer is replaced in these tests")


def _service(
    repository: FakeDatasetRepository | JsonDatasetRepository,
    orchestrator: FakeOrchestratorClient,
) -> EvaluationService:
    return EvaluationService(
        config=_config(),
        dataset_repository=repository,
        orchestrator_client=orchestrator,
        judge_client=UnusedJudgeClient(),
        admin_groups=frozenset({"rag_admin"}),
    )


def test_json_dataset_repository_validates_all_items(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            [
                {"question": "Q1", "reference_answer": "R1"},
                {"question": "", "reference_answer": "R2"},
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(DatasetException) as exc_info:
        JsonDatasetRepository(dataset_path).load()

    assert exc_info.value.details["errors"] == 1


@pytest.mark.asyncio
async def test_invalid_dataset_is_rejected_before_external_call(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        '[{"question":"Q","reference_answer":""}]', encoding="utf-8"
    )
    orchestrator = FakeOrchestratorClient()

    with pytest.raises(DatasetException):
        await _service(JsonDatasetRepository(dataset_path), orchestrator).evaluate(
            "token"
        )

    assert orchestrator.auth_tokens == ["token"]
    assert orchestrator.question_calls == []


def test_build_empty_evaluation_response_returns_zero_scores() -> None:
    response = build_empty_evaluation_response()

    assert response.total_questions == 0
    assert response.average_retrieval.mrr == 0.0
    assert response.average_answer_quality.feedback == "Aucune évaluation"


def test_retrieval_accumulator_and_average() -> None:
    accumulator = build_retrieval_accumulator()
    add_retrieval_score(
        accumulator,
        RetrievalEvaluationBase(mrr=1, ndcg=0.5, recall=0.25, precision=0.75),
    )
    add_retrieval_score(
        accumulator,
        RetrievalEvaluationBase(mrr=0, ndcg=0.5, recall=0.75, precision=0.25),
    )

    average = calculate_average_retrieval(accumulator, total_questions=2)

    assert average.mrr == 0.5
    assert average.ndcg == 0.5
    assert average.recall == 0.5
    assert average.precision == 0.5


def test_quality_accumulator_and_average() -> None:
    accumulator = build_quality_accumulator()
    add_quality_score(
        accumulator,
        AnswerEvaluationBase(feedback="ok", accuracy=4, completeness=3, relevance=5),
    )
    add_quality_score(
        accumulator,
        AnswerEvaluationBase(feedback="ok", accuracy=2, completeness=5, relevance=3),
    )

    average = calculate_average_quality(accumulator, valid_judgements=2)

    assert average.accuracy == 3
    assert average.completeness == 4
    assert average.relevance == 4


def test_quality_average_rejects_missing_judgements() -> None:
    with pytest.raises(ValueError, match="jugement valide"):
        calculate_average_quality(build_quality_accumulator(), valid_judgements=0)


@pytest.mark.asyncio
async def test_evaluation_service_averages_successful_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeDatasetRepository(
        [
            EvaluationCase(question="Q1", reference_answer="R1", keywords=["keyword"]),
            EvaluationCase(question="Q2", reference_answer="R2", keywords=["keyword"]),
        ]
    )

    async def fake_evaluate_answer(**kwargs: object) -> AnswerEvaluationBase:
        return AnswerEvaluationBase(
            feedback="ok", accuracy=4, completeness=3, relevance=5
        )

    monkeypatch.setattr(evaluating_service, "evaluate_answer", fake_evaluate_answer)

    orchestrator = FakeOrchestratorClient(groups=["RAG_ADMIN"])
    result = await _service(repository, orchestrator).evaluate("same-token")

    assert result.total_questions == 2
    assert result.average_retrieval.mrr == 1
    assert result.average_answer_quality.accuracy == 4
    assert orchestrator.auth_tokens == ["same-token"]
    assert orchestrator.question_calls == [
        ("Q1", "same-token"),
        ("Q2", "same-token"),
    ]


@pytest.mark.asyncio
async def test_evaluation_rejects_user_without_admin_group() -> None:
    repository = FakeDatasetRepository(
        [EvaluationCase(question="Q", reference_answer="R")]
    )
    orchestrator = FakeOrchestratorClient(groups=["developers"])

    with pytest.raises(EvaluatorAuthorizationError, match="administrateur"):
        await _service(repository, orchestrator).evaluate("token")

    assert orchestrator.question_calls == []


@pytest.mark.asyncio
async def test_orchestrator_failure_aborts_evaluation() -> None:
    repository = FakeDatasetRepository(
        [EvaluationCase(question="Q", reference_answer="R")]
    )
    orchestrator = FakeOrchestratorClient(EvaluatorClientError("rag down"))

    with pytest.raises(EvaluatorClientError, match="rag down"):
        await _service(repository, orchestrator).evaluate("token")


@pytest.mark.asyncio
async def test_judge_failure_aborts_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeDatasetRepository(
        [EvaluationCase(question="Q", reference_answer="R")]
    )

    async def failing_evaluate_answer(**kwargs: object) -> AnswerEvaluationBase:
        raise EvaluatorClientError("judge down")

    monkeypatch.setattr(evaluating_service, "evaluate_answer", failing_evaluate_answer)

    with pytest.raises(EvaluatorClientError, match="judge down"):
        await _service(repository, FakeOrchestratorClient()).evaluate("token")
