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

        # Payload à plat pour OpenAI
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "temperature": config["llm"]["temperature"],
            "max_tokens": config["llm"]["max_tokens"],
        }
        judge_json = await judge_client_api_openia(payload, timeout, base_url, api_key)
    else:
        # Appel classique Ollama
        judge_json = await judge_client(config, messages)

    raw = judge_json["llm_answer"]  # <- la string renvoyée par le LLM
    judge_out = judge_parser.parse(raw)  # <- -> JudgeOutput (validé)

    return AnswerEvaluationBase.model_validate(judge_out.model_dump())
