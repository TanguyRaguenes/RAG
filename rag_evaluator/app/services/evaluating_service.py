import json
import os
from typing import Any

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


def load_dataset() -> list[dict[str, Any]]:
    dataset_path = os.getenv("DATASET_PATH")
    if not dataset_path:
        raise ValueError("DATASET_PATH must be configured")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("dataset.json doit contenir une liste d'objets")

    return data


async def evaluate_rag(config: dict) -> EvaluatorResponseBase:
    tests = load_dataset()
    nb_questions = len(tests)

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
            # 1° On pose la question à notre RAG
            raw_data: dict = await ask_question(question)
            data = AskQuestionResponseBase(**raw_data)

            rag_answer = data.llm_response
            retrieved_chunks: list[ChunkBase] = data.retrieved_chunks

        except Exception as e:
            print(e)
            rag_answer = ""
            retrieved_chunks = []

        # 2° On calcule les métriques sur les chunks récupérés par notre RAG (MRR, nDCG, recall@K, precision@K)
        retrieval_evaluation_response = evaluate_retrieval(
            keywords=keywords, retrieved_chunks=retrieved_chunks, k=5
        )
        add_retrieval_score(acc_retrieval, retrieval_evaluation_response)

        # 3° On demande à un autre LLM son avis sur la réponse de notre RAG
        try:
            answer_evaluation_response: AnswerEvaluationBase = await evaluate_answer(
                config=config,
                question=question,
                reference_answer=ref_answer,
                generated_answer=rag_answer,
                retrieved_chunks=retrieved_chunks,
            )

            add_quality_score(acc_quality, answer_evaluation_response)
            valid_judgements += 1

        except Exception as e:
            print(e)

    return EvaluatorResponseBase(
        average_retrieval=calculate_average_retrieval(acc_retrieval, nb_questions),
        average_answer_quality=calculate_average_quality(
            acc_quality,
            valid_judgements,
        ),
        total_duration="00:00",
        total_questions=nb_questions,
    )


def build_empty_evaluation_response() -> EvaluatorResponseBase:
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
    return {"mrr": 0.0, "ndcg": 0.0, "recall": 0.0, "precision": 0.0}


def build_quality_accumulator() -> QualityAccumulator:
    return {"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}


def add_retrieval_score(
    accumulator: RetrievalAccumulator,
    retrieval_evaluation: RetrievalEvaluationBase,
) -> None:
    accumulator["mrr"] += retrieval_evaluation.mrr
    accumulator["ndcg"] += retrieval_evaluation.ndcg
    accumulator["recall"] += retrieval_evaluation.recall
    accumulator["precision"] += retrieval_evaluation.precision


def add_quality_score(
    accumulator: QualityAccumulator,
    answer_evaluation: AnswerEvaluationBase,
) -> None:
    accumulator["accuracy"] += answer_evaluation.accuracy
    accumulator["completeness"] += answer_evaluation.completeness
    accumulator["relevance"] += answer_evaluation.relevance


def calculate_average_retrieval(
    accumulator: RetrievalAccumulator,
    total_questions: int,
) -> RetrievalEvaluationBase:
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
    divisor = valid_judgements if valid_judgements > 0 else 1

    return AnswerEvaluationBase(
        feedback="Moyenne Globale du Dataset",
        accuracy=round(accumulator["accuracy"] / divisor, 2),
        completeness=round(accumulator["completeness"] / divisor, 2),
        relevance=round(accumulator["relevance"] / divisor, 2),
    )
