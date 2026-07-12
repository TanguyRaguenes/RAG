import os
from typing import Any

from app.dal.client.judge_client import judge_client, judge_client_api_openia
from app.domain.models.judge_response_model import judge_parser
from app.schemas.Answer_evaluation_schema import AnswerEvaluationBase
from app.services.prompt_builder_service import build_judge_messages


async def evaluate_answer(
    config: dict,
    question: str,
    generated_answer: str,
    reference_answer: str,
    retrieved_chunks: list[dict[str, Any]],
) -> AnswerEvaluationBase:
    """Demande au juge LLM d'évaluer la réponse générée par le RAG.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        question: Question utilisateur traitée par le pipeline RAG, sans journalisation du contenu complet.
        generated_answer: Réponse produite par le RAG à évaluer.
        reference_answer: Réponse attendue du dataset d'évaluation.
        retrieved_chunks: Chunks retournés par le retriever ou l'orchestrator.

    Returns:
        Scores JSON produits par le juge LLM pour la réponse RAG.
    """
    messages = build_judge_messages(
        question=question,
        generated_answer=generated_answer,
        reference_answer=reference_answer,
        retrieved_chunks=retrieved_chunks,
        max_context_chars=12000,
    )

    use_api_openai = config["evaluation_method"]["use_api_openai"]
    if use_api_openai:
        api_key = os.getenv("OPEN_API_KEY")

        base_url = "https://api.openai.com/v1/chat/completions"
        timeout = config["llm"]["timeout_seconds"]

        # Payload à plat pour API
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": config["llm"]["temperature"],
            "max_output_token": config["llm"]["max_output_token"],
        }
        judge_json = await judge_client_api_openia(payload, timeout, base_url, api_key)
    else:
        # Appel classique Ollama
        judge_json = await judge_client(config, messages)

    raw = judge_json["llm_answer"]  # <- la string renvoyée par le LLM
    judge_out = judge_parser.parse(raw)  # <- -> JudgeOutput (validé)

    return AnswerEvaluationBase.model_validate(judge_out.model_dump())
