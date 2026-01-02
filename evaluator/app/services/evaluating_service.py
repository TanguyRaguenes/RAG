import json
import os
from typing import Any

from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase

from app.dal.client.rag_api_client import rag_api_client
from app.dal.client.judge_client import judge_client

from app.services.evaluating_retrieval import evaluate_retrieval
from app.services.evaluating_answer import evaluate_answer


def load_dataset() -> list[dict[str, Any]]:
    dataset_path = os.getenv("DATASET_PATH")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("dataset.json doit contenir une liste d'objets")
    return data


def _empty_retrieval() -> RetrievalEvaluationBase:
    return RetrievalEvaluationBase(mrr=0, ndcg=0, keywords_found=0, total_keywords=0, keyword_coverage=0)


def _empty_answer() -> AnswerEvaluationBase:
    return AnswerEvaluationBase(feedback="Aucune évaluation", accuracy=0, completeness=0, relevance=0)


async def evaluate_rag(config: dict) -> EvaluatorResponseBase:
    tests = load_dataset()
    nb_questions = len(tests)

    if nb_questions == 0:
        return EvaluatorResponseBase(
            average_retrieval=_empty_retrieval(),
            average_quality=_empty_answer(),
            total_duration="00:00",
            total_questions=0,
        )

    # ---- accumulateurs ----
    acc_retrieval = {"mrr": 0.0, "ndcg": 0.0, "coverage": 0.0}
    acc_quality = {"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}
    valid_judgements = 0


    for test in tests:

        question = test["question"]
        keywords = test.get("keywords")
        ref_answer = test["reference_answer"]

        rag_answer = ""
        chunks: list[dict[str, Any]] = []
        try:
            data = await rag_api_client(question)
            rag_api_response = data.get("answer")
            rag_answer = rag_api_response.get("llm_answer") or rag_api_response.get("answer") or ""
            raw_chunks = rag_api_response.get("chunks") or rag_api_response.get("chuncks") or []
            chunks = raw_chunks if isinstance(raw_chunks, list) else []
        except Exception:
            rag_answer = ""
            chunks = []

        # Retrieval evaluation (math)
        retrieval_evaluation_response = evaluate_retrieval(keywords=keywords, raw_chunks=chunks, k=5)
        acc_retrieval["mrr"] += retrieval_evaluation_response.mrr
        acc_retrieval["ndcg"] += retrieval_evaluation_response.ndcg
        acc_retrieval["coverage"] += retrieval_evaluation_response.keyword_coverage

        # Answer evaluation (judge)
        try:
            answer_evaluation_response = await evaluate_answer(
                config=config,
                question=question,
                reference_answer=ref_answer,
                generated_answer=rag_answer,
                chunks=chunks,
            )
            acc_quality["accuracy"] += answer_evaluation_response.accuracy
            acc_quality["completeness"] += answer_evaluation_response.completeness
            acc_quality["relevance"] += answer_evaluation_response.relevance
            valid_judgements += 1
        except Exception as e:
            print(e)
            pass

    # ---- moyennes ----
    avg_retrieval = RetrievalEvaluationBase(
        mrr=round(acc_retrieval["mrr"] / nb_questions, 4),
        ndcg=round(acc_retrieval["ndcg"] / nb_questions, 4),
        keyword_coverage=round(acc_retrieval["coverage"] / nb_questions, 2),
        keywords_found=0,
        total_keywords=0,
    )

    div_q = valid_judgements if valid_judgements > 0 else 1
    avg_quality = AnswerEvaluationBase(
        feedback="Moyenne Globale du Dataset",
        accuracy=round(acc_quality["accuracy"] / div_q, 2),
        completeness=round(acc_quality["completeness"] / div_q, 2),
        relevance=round(acc_quality["relevance"] / div_q, 2),
    )

    return EvaluatorResponseBase(
        average_retrieval=avg_retrieval,
        average_quality=avg_quality,
        total_duration="00:00",
        total_questions=nb_questions,
    )
