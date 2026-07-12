import json
import logging
import os
from typing import Any

from opentelemetry import trace

from app.core.exceptions import DatasetException
from app.core.metrics import evaluator_questions_total, evaluator_score
from app.dal.client.rag_orchestrator_client import ask_question
from app.domain.models.ask_question_response_model import AskQuestionResponseBase
from app.domain.models.chunk_model import ChunkBase
from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.evaluating_answer_service import evaluate_answer
from app.services.evaluating_retrieval_service import evaluate_retrieval

RetrievalAccumulator = dict[str, float]
QualityAccumulator = dict[str, float]
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def load_dataset() -> list[dict[str, Any]]:
    """Charge le dataset d'évaluation depuis le chemin configuré.

    Returns:
        Liste de cas de test d'évaluation.

    Raises:
        DatasetException: Si `DATASET_PATH` manque, si le JSON est invalide ou si le format racine n'est pas une liste.
        OSError: Si le fichier dataset ne peut pas être lu.
    """
    dataset_path = os.getenv("DATASET_PATH")
    if not dataset_path:
        raise DatasetException(
            message="DATASET_PATH doit être configuré",
            details={"env_var": "DATASET_PATH"},
        )

    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exception:
        raise DatasetException(
            message="Dataset JSON invalide",
            details={"path": dataset_path},
        ) from exception

    if not isinstance(data, list):
        raise DatasetException(
            message="dataset.json doit contenir une liste d'objets",
            details={"path": dataset_path, "actual_type": type(data).__name__},
        )

    return data


async def evaluate_rag(config: dict) -> EvaluatorResponseBase:
    """Évalue le RAG sur toutes les questions du dataset.

    Args:
        config: Configuration applicative contenant le juge LLM et la stratégie d'évaluation.

    Returns:
        Scores moyens de retrieval et de qualité de réponse.

    Raises:
        DatasetException: Si le dataset ne peut pas être chargé.
    """
    with tracer.start_as_current_span("evaluator.evaluate_dataset") as span:
        tests = load_dataset()
        nb_questions = len(tests)
        span.set_attribute("evaluation.question_count", nb_questions)

        if nb_questions == 0:
            return build_empty_evaluation_response()

        acc_retrieval = build_retrieval_accumulator()
        acc_quality = build_quality_accumulator()
        valid_judgements = 0

        for test in tests:
            question = test["question"]
            keywords = test.get("keywords")
            ref_answer = test["reference_answer"]

            rag_answer: str = ""
            retrieved_chunks: list[dict[str, Any]] = []

            try:
                raw_data: dict = await ask_question(question)
                data = AskQuestionResponseBase(**raw_data)

                rag_answer = data.llm_response
                retrieved_chunks: list[ChunkBase] = data.retrieved_chunks
                evaluator_questions_total.labels(status="rag_success").inc()

            except Exception as exception:
                logger.exception(
                    "evaluation rag call failed",
                    extra={
                        "service": "rag_evaluator",
                        "event": "rag_call_failed",
                        "error_type": type(exception).__name__,
                    },
                )
                evaluator_questions_total.labels(status="rag_error").inc()
                rag_answer = ""
                retrieved_chunks = []

            retrieval_evaluation_response = evaluate_retrieval(
                keywords=keywords, retrieved_chunks=retrieved_chunks, k=5
            )
            add_retrieval_score(acc_retrieval, retrieval_evaluation_response)

            try:
                answer_evaluation_response: AnswerEvaluationBase = (
                    await evaluate_answer(
                        config=config,
                        question=question,
                        reference_answer=ref_answer,
                        generated_answer=rag_answer,
                        retrieved_chunks=retrieved_chunks,
                    )
                )

                add_quality_score(acc_quality, answer_evaluation_response)
                valid_judgements += 1
                evaluator_questions_total.labels(status="judge_success").inc()

            except Exception as exception:
                logger.exception(
                    "evaluation judge call failed",
                    extra={
                        "service": "rag_evaluator",
                        "event": "judge_call_failed",
                        "error_type": type(exception).__name__,
                    },
                )
                evaluator_questions_total.labels(status="judge_error").inc()

        response = EvaluatorResponseBase(
            average_retrieval=calculate_average_retrieval(acc_retrieval, nb_questions),
            average_answer_quality=calculate_average_quality(
                acc_quality,
                valid_judgements,
            ),
            total_duration="00:00",
            total_questions=nb_questions,
        )
        _record_scores(response)
        return response


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
        ),
        average_answer_quality=AnswerEvaluationBase(
            feedback="Aucune évaluation",
            accuracy=0,
            completeness=0,
            relevance=0,
        ),
        total_duration="00:00",
        total_questions=0,
    )


def build_retrieval_accumulator() -> RetrievalAccumulator:
    """Construit l'accumulateur des métriques de retrieval.

    Returns:
        Dictionnaire initialisé pour MRR, nDCG, recall et precision.
    """
    return {"mrr": 0.0, "ndcg": 0.0, "recall": 0.0, "precision": 0.0}


def build_quality_accumulator() -> QualityAccumulator:
    """Construit l'accumulateur des métriques de qualité de réponse.

    Returns:
        Dictionnaire initialisé pour accuracy, completeness et relevance.
    """
    return {"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}


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
        Scores moyens de qualité, avec diviseur sécurisé si aucun jugement n'est valide.
    """
    divisor = valid_judgements if valid_judgements > 0 else 1

    return AnswerEvaluationBase(
        feedback="Moyenne Globale du Dataset",
        accuracy=round(accumulator["accuracy"] / divisor, 2),
        completeness=round(accumulator["completeness"] / divisor, 2),
        relevance=round(accumulator["relevance"] / divisor, 2),
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
    evaluator_score.labels(metric="accuracy").set(
        response.average_answer_quality.accuracy
    )
    evaluator_score.labels(metric="completeness").set(
        response.average_answer_quality.completeness
    )
    evaluator_score.labels(metric="relevance").set(
        response.average_answer_quality.relevance
    )
