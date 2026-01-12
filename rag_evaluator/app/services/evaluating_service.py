import json
import os
from typing import Any

from app.dal.client.rag_api_client import ask_question
from app.domain.models.rag_response_model import RagResponseBase
from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.schemas.evaluator_response_schema import EvaluatorResponseBase
from app.schemas.retrieval_evaluation_schema import RetrievalEvaluationBase
from app.services.evaluating_answer import evaluate_answer
from app.services.evaluating_retrieval import evaluate_retrieval


def load_dataset() -> list[dict[str, Any]]:
    dataset_path = os.getenv("DATASET_PATH")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("dataset.json doit contenir une liste d'objets")
    return data


async def evaluate_rag(config: dict) -> EvaluatorResponseBase:
    tests = load_dataset()
    nb_questions = len(tests)

    if nb_questions == 0:
        return EvaluatorResponseBase(
            average_retrieval=RetrievalEvaluationBase(
                mrr=0.0, ndcg=0.0, recall=0.0, precision=0.0
            ),
            average_answer_quality=AnswerEvaluationBase(
                feedback="Aucune évaluation", accuracy=0, completeness=0, relevance=0
            ),
            total_duration="00:00",
            total_questions=0,
        )

    # ---- accumulateurs ----
    acc_retrieval = {"mrr": 0.0, "ndcg": 0.0, "recall": 0.0, "precision": 0.0}
    acc_quality = {"accuracy": 0.0, "completeness": 0.0, "relevance": 0.0}
    valid_judgements = 0

    for test in tests:
        question = test["question"]
        keywords = test.get("keywords")
        ref_answer = test["reference_answer"]

        rag_answer = ""
        retrieved_chunks: list[dict[str, Any]] = []

        try:
            # 1° On pose la question à notre RAG
            raw_data: dict = await ask_question(question)
            data: RagResponseBase = RagResponseBase(**raw_data)

            rag_api_response = data.answer
            rag_answer = rag_api_response.llm_answer
            retrieved_chunks = rag_api_response.chunks

        except Exception as e:
            print(e)
            rag_answer = ""
            retrieved_chunks = []

        # 2° On calcule les métriques sur les chunks récupérés par notre RAG (MRR, nDCG, recall@K, precision@K)
        retrieval_evaluation_response = evaluate_retrieval(
            keywords=keywords, retrieved_chunks=retrieved_chunks, k=5
        )

        acc_retrieval["mrr"] += retrieval_evaluation_response.mrr
        acc_retrieval["ndcg"] += retrieval_evaluation_response.ndcg
        acc_retrieval["recall"] += retrieval_evaluation_response.recall
        acc_retrieval["precision"] += retrieval_evaluation_response.precision

        # 3° On demande à un autre LLM son avis sur la réponse de notre RAG
        try:
            answer_evaluation_response: AnswerEvaluationBase = await evaluate_answer(
                config=config,
                question=question,
                reference_answer=ref_answer,
                generated_answer=rag_answer,
                retrieved_chunks=retrieved_chunks,
            )

            acc_quality["accuracy"] += answer_evaluation_response.accuracy
            acc_quality["completeness"] += answer_evaluation_response.completeness
            acc_quality["relevance"] += answer_evaluation_response.relevance
            valid_judgements += 1

        except Exception as e:
            print(e)

    # ---- moyennes ----
    avg_retrieval = RetrievalEvaluationBase(
        mrr=round(acc_retrieval["mrr"] / nb_questions, 4),
        ndcg=round(acc_retrieval["ndcg"] / nb_questions, 4),
        recall=round(acc_retrieval["recall"] / nb_questions, 4),
        precision=round(acc_retrieval["precision"] / nb_questions, 4),
    )

    div_q = valid_judgements if valid_judgements > 0 else 1

    avg_answer_quality = AnswerEvaluationBase(
        feedback="Moyenne Globale du Dataset",
        accuracy=round(acc_quality["accuracy"] / div_q, 2),
        completeness=round(acc_quality["completeness"] / div_q, 2),
        relevance=round(acc_quality["relevance"] / div_q, 2),
    )

    return EvaluatorResponseBase(
        average_retrieval=avg_retrieval,
        average_answer_quality=avg_answer_quality,
        total_duration="00:00",
        total_questions=nb_questions,
    )
