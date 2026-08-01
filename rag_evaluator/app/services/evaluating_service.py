from typing import Any

from opentelemetry import trace

from app.core.config import EvaluatorConfig, load_admin_groups
from app.core.exceptions import EvaluatorAuthorizationError
from app.core.metrics import evaluator_questions_total, evaluator_score
from app.dal.clients.dataset_repository import (
    DatasetRepository,
    JsonDatasetRepository,
)
from app.dal.clients.judge_client import ConfiguredJudgeClient, JudgeClient
from app.dal.clients.rag_orchestrator_client import (
    HttpRagOrchestratorClient,
    RagOrchestratorClient,
)
from app.schemas.answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.dataset_schema import EvaluationCase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.orchestrator_schema import AskQuestionResponse, AuthenticatedUser
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.evaluating_answer_service import evaluate_answer
from app.services.evaluating_retrieval_service import evaluate_retrieval

RetrievalAccumulator = dict[str, float]
QualityAccumulator = dict[str, float]
tracer = trace.get_tracer(__name__)


def load_dataset() -> list[EvaluationCase]:
    """Charge le dataset via le repository de la couche DAL.

    Returns:
        Liste intégralement validée des cas d'évaluation.

    Raises:
        DatasetException: Si la configuration, la lecture ou la validation échoue.
    """
    return JsonDatasetRepository.from_environment().load()


class EvaluationService:
    """Orchestre l'évaluation sans dépendre des transports concrets."""

    def __init__(
        self,
        config: EvaluatorConfig,
        dataset_repository: DatasetRepository,
        orchestrator_client: RagOrchestratorClient,
        judge_client: JudgeClient,
        admin_groups: frozenset[str],
    ) -> None:
        """Injecte la configuration et les frontières externes.

        Args:
            config: Configuration applicative validée.
            dataset_repository: Source des cas d'évaluation.
            orchestrator_client: Client du RAG à mesurer.
            judge_client: Client du modèle chargé de juger les réponses.
            admin_groups: Groupes autorisés, normalisés en minuscules.
        """
        self._config = config
        self._dataset_repository = dataset_repository
        self._orchestrator_client = orchestrator_client
        self._judge_client = judge_client
        self._admin_groups = admin_groups

    async def evaluate(self, access_token: str) -> EvaluatorResponseBase:
        """Évalue chaque cas après validation complète du dataset.

        Args:
            access_token: Bearer vérifié puis propagé à chaque appel orchestrator.

        Returns:
            Moyennes calculées uniquement à partir d'appels tous réussis.

        Raises:
            DatasetException: Si le dataset complet n'est pas valide.
            EvaluatorClientError: Si l'orchestrator ou le juge est indisponible.
            JudgeEvaluationException: Si le jugement LLM est absent ou invalide.
        """
        with tracer.start_as_current_span("evaluator.evaluate_dataset") as span:
            await self._authorize(access_token)
            tests = self._dataset_repository.load()
            total_questions = len(tests)
            span.set_attribute("evaluation.question_count", total_questions)

            if total_questions == 0:
                return build_empty_evaluation_response()

            retrieval_scores = build_retrieval_accumulator()
            quality_scores = build_quality_accumulator()

            for test in tests:
                rag_response = await self._ask_question(test.question, access_token)
                retrieved_chunks = [
                    chunk.model_dump() for chunk in rag_response.retrieved_chunks
                ]
                retrieval_evaluation = evaluate_retrieval(
                    keywords=test.keywords,
                    retrieved_chunks=retrieved_chunks,
                    k=5,
                    expected_sources=test.expected_sources,
                )
                add_retrieval_score(retrieval_scores, retrieval_evaluation)

                answer_evaluation = await self._evaluate_answer(
                    test=test,
                    generated_answer=rag_response.llm_response,
                    retrieved_chunks=retrieved_chunks,
                )
                add_quality_score(quality_scores, answer_evaluation)

            response = EvaluatorResponseBase(
                average_retrieval=calculate_average_retrieval(
                    retrieval_scores, total_questions
                ),
                average_answer_quality=calculate_average_quality(
                    quality_scores, total_questions
                ),
                total_duration="00:00",
                total_questions=total_questions,
            )
            _record_scores(response)
            return response

    async def _authorize(self, access_token: str) -> AuthenticatedUser:
        """Vérifie l'identité puis exige un groupe administrateur.

        Args:
            access_token: Bearer opaque transmis à `/auth/me`.

        Returns:
            Identité authentifiée autorisée à lancer l'évaluation.

        Raises:
            EvaluatorAuthenticationError: Si le bearer n'est pas accepté.
            EvaluatorAuthorizationError: Si aucun groupe admin ne correspond.
            EvaluatorClientError: Si l'orchestrator ne peut pas vérifier l'identité.
        """
        user = await self._orchestrator_client.get_current_user(access_token)
        user_groups = {
            group.strip().casefold() for group in user.groups if group.strip()
        }
        if not user_groups.intersection(self._admin_groups):
            raise EvaluatorAuthorizationError(
                message="Un groupe administrateur evaluator est requis"
            )
        return user

    async def _ask_question(
        self, question: str, access_token: str
    ) -> AskQuestionResponse:
        """Appelle le RAG en enregistrant le statut de la question.

        Args:
            question: Question validée issue du dataset.
            access_token: Bearer autorisé à propager vers l'orchestrator.

        Returns:
            Réponse structurée de l'orchestrator.

        Raises:
            EvaluatorClientError: Si l'appel externe échoue.
        """
        try:
            response = await self._orchestrator_client.ask_question(
                question, access_token
            )
        except Exception:
            evaluator_questions_total.labels(status="rag_error").inc()
            raise
        evaluator_questions_total.labels(status="rag_success").inc()
        return response

    async def _evaluate_answer(
        self,
        test: EvaluationCase,
        generated_answer: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> AnswerEvaluationBase:
        """Juge une réponse en enregistrant le statut de l'opération.

        Args:
            test: Cas validé contenant les attentes métier.
            generated_answer: Réponse produite par le RAG.
            retrieved_chunks: Contexte documentaire retourné par l'orchestrator.

        Returns:
            Scores validés du juge.

        Raises:
            EvaluatorClientError: Si le fournisseur de jugement échoue.
            JudgeEvaluationException: Si sa réponse est inexploitable.
        """
        try:
            response = await evaluate_answer(
                config=self._config,
                question=test.question,
                reference_answer=test.reference_answer,
                generated_answer=generated_answer,
                retrieved_chunks=retrieved_chunks,
                expected_answer_points=test.expected_answer_points,
                expected_behavior=test.expected_behavior,
                judge_client=self._judge_client,
            )
        except Exception:
            evaluator_questions_total.labels(status="judge_error").inc()
            raise
        evaluator_questions_total.labels(status="judge_success").inc()
        return response


async def evaluate_rag(
    config: EvaluatorConfig | dict[str, Any],
    access_token: str,
) -> EvaluatorResponseBase:
    """Évalue le RAG sur toutes les questions du dataset.

    Args:
        config: Configuration applicative contenant le juge et la stratégie d'évaluation.
        access_token: Bearer de la requête HTTP à vérifier et propager.

    Returns:
        Scores moyens de retrieval et de qualité de réponse.

    Raises:
        EvaluatorContainerCustomException: Si une frontière externe échoue.
    """
    typed_config = EvaluatorConfig.model_validate(config)
    service = EvaluationService(
        config=typed_config,
        dataset_repository=JsonDatasetRepository.from_environment(),
        orchestrator_client=HttpRagOrchestratorClient.from_environment(
            typed_config.rag_provider
        ),
        judge_client=ConfiguredJudgeClient.from_config(typed_config),
        admin_groups=load_admin_groups(),
    )
    return await service.evaluate(access_token)


def build_empty_evaluation_response() -> EvaluatorResponseBase:
    """Construit une réponse d'évaluation vide.

    Returns:
        Réponse contenant des scores nuls et un message explicite.
    """
    return EvaluatorResponseBase(
        average_retrieval=RetrievalEvaluationBase(
            mrr=0.0,
            ndcg=0.0,
            recall=0.0,
            precision=0.0,
            source_hit_at_5=0.0,
        ),
        average_answer_quality=AnswerEvaluationBase(
            feedback="Aucune évaluation",
            accuracy=0,
            completeness=0,
            relevance=0,
            faithfulness=0,
            safe_refusal=0,
        ),
        total_duration="00:00",
        total_questions=0,
    )


def build_retrieval_accumulator() -> RetrievalAccumulator:
    """Construit l'accumulateur des métriques de retrieval.

    Returns:
        Dictionnaire initialisé pour MRR, nDCG, recall, precision et source hit.
    """
    return {
        "mrr": 0.0,
        "ndcg": 0.0,
        "recall": 0.0,
        "precision": 0.0,
        "source_hit_at_5": 0.0,
    }


def build_quality_accumulator() -> QualityAccumulator:
    """Construit l'accumulateur des métriques de qualité de réponse.

    Returns:
        Dictionnaire initialisé pour les métriques de qualité de réponse.
    """
    return {
        "accuracy": 0.0,
        "completeness": 0.0,
        "relevance": 0.0,
        "faithfulness": 0.0,
        "safe_refusal": 0.0,
    }


def add_retrieval_score(
    accumulator: RetrievalAccumulator,
    retrieval_evaluation: RetrievalEvaluationBase,
) -> None:
    """Ajoute les scores de retrieval à l'accumulateur.

    Args:
        accumulator: Accumulateur mutable des scores retrieval.
        retrieval_evaluation: Scores calculés pour une question.

    Returns:
        Aucune valeur.
    """
    accumulator["mrr"] += retrieval_evaluation.mrr
    accumulator["ndcg"] += retrieval_evaluation.ndcg
    accumulator["recall"] += retrieval_evaluation.recall
    accumulator["precision"] += retrieval_evaluation.precision
    accumulator["source_hit_at_5"] += retrieval_evaluation.source_hit_at_5


def add_quality_score(
    accumulator: QualityAccumulator,
    answer_evaluation: AnswerEvaluationBase,
) -> None:
    """Ajoute les scores de qualité à l'accumulateur.

    Args:
        accumulator: Accumulateur mutable des scores qualité.
        answer_evaluation: Scores calculés par le juge LLM.

    Returns:
        Aucune valeur.
    """
    accumulator["accuracy"] += answer_evaluation.accuracy
    accumulator["completeness"] += answer_evaluation.completeness
    accumulator["relevance"] += answer_evaluation.relevance
    accumulator["faithfulness"] += answer_evaluation.faithfulness
    accumulator["safe_refusal"] += answer_evaluation.safe_refusal


def calculate_average_retrieval(
    accumulator: RetrievalAccumulator,
    total_questions: int,
) -> RetrievalEvaluationBase:
    """Calcule les moyennes des scores de retrieval.

    Args:
        accumulator: Sommes des scores retrieval.
        total_questions: Nombre total de questions évaluées.

    Returns:
        Scores moyens de retrieval arrondis.

    Raises:
        ZeroDivisionError: Si `total_questions` vaut zéro.
    """
    return RetrievalEvaluationBase(
        mrr=round(accumulator["mrr"] / total_questions, 4),
        ndcg=round(accumulator["ndcg"] / total_questions, 4),
        recall=round(accumulator["recall"] / total_questions, 4),
        precision=round(accumulator["precision"] / total_questions, 4),
        source_hit_at_5=round(accumulator["source_hit_at_5"] / total_questions, 4),
    )


def calculate_average_quality(
    accumulator: QualityAccumulator,
    valid_judgements: int,
) -> AnswerEvaluationBase:
    """Calcule les moyennes des scores de qualité de réponse.

    Args:
        accumulator: Sommes des scores de qualité.
        valid_judgements: Nombre de jugements LLM valides.

    Returns:
        Scores moyens calculés sur les jugements valides.

    Raises:
        ValueError: Si aucun jugement valide n'est disponible.
    """
    if valid_judgements <= 0:
        raise ValueError("Au moins un jugement valide est requis")

    return AnswerEvaluationBase(
        feedback="Moyenne Globale du Dataset",
        accuracy=round(accumulator["accuracy"] / valid_judgements, 2),
        completeness=round(accumulator["completeness"] / valid_judgements, 2),
        relevance=round(accumulator["relevance"] / valid_judgements, 2),
        faithfulness=round(accumulator["faithfulness"] / valid_judgements, 2),
        safe_refusal=round(accumulator["safe_refusal"] / valid_judgements, 2),
    )


def _record_scores(response: EvaluatorResponseBase) -> None:
    """Expose les derniers scores moyens sous forme de gauges Prometheus.

    Args:
        response: Réponse d'évaluation contenant les scores moyens.

    Returns:
        Aucune valeur.
    """
    evaluator_score.labels(metric="mrr").set(response.average_retrieval.mrr)
    evaluator_score.labels(metric="ndcg").set(response.average_retrieval.ndcg)
    evaluator_score.labels(metric="recall").set(response.average_retrieval.recall)
    evaluator_score.labels(metric="precision").set(response.average_retrieval.precision)
    evaluator_score.labels(metric="source_hit_at_5").set(
        response.average_retrieval.source_hit_at_5
    )
    evaluator_score.labels(metric="accuracy").set(
        response.average_answer_quality.accuracy
    )
    evaluator_score.labels(metric="completeness").set(
        response.average_answer_quality.completeness
    )
    evaluator_score.labels(metric="relevance").set(
        response.average_answer_quality.relevance
    )
    evaluator_score.labels(metric="faithfulness").set(
        response.average_answer_quality.faithfulness
    )
    evaluator_score.labels(metric="safe_refusal").set(
        response.average_answer_quality.safe_refusal
    )
