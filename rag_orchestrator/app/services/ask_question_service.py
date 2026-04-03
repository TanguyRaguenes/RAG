import os
from typing import Any

from app.dal.clients.embedder_client import embed_question
from app.dal.clients.llm_client import ask_question_to_api as ask_question_to_api_client
from app.dal.clients.llm_client import ask_question_to_llm as ask_question_to_llm_client
from app.dal.clients.retriever_client import retrieve_chunks
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.services.prompt_builder_service import build_prompt


async def ask_question_to_local_model(
    question: str, config: dict
) -> AskQuestionResponseBase:

    timeout_seconds: int = config["llm"]["common"]["timeout_seconds"]
    temperature: float = config["llm"]["common"]["temperature"]
    stream: bool = config["llm"]["common"]["stream"]

    endpoint: str = config["llm"]["local"]["endpoint"]
    model: str = config["llm"]["local"]["model"]
    max_output_tokens: int = config["llm"]["local"]["max_output_tokens"]
    context_window_tokens: int = config["llm"]["local"]["context_window_tokens"]
    max_prompt_chars = config["llm"]["local"]["max_prompt_chars"]

    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks(embeded_question)

    prompt: list[dict[str, str]] = build_prompt(
        question, retrieved_chunks, max_prompt_chars
    )

    payload: dict[str, Any] = {
        "model": model,
        "messages": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_ctx": context_window_tokens,
            "num_predict": max_output_tokens,
        },
    }

    llm_response = await ask_question_to_llm_client(payload, timeout_seconds, endpoint)

    sources: dict[str, int] = design_source(retrieved_chunks)

    return AskQuestionResponseBase(
        llm_response=llm_response["choices"][0]["message"]["content"],
        retrieved_chunks=retrieved_chunks,
        retrieved_documents=sources,
        model=model,
        generated_prompt=prompt,
        duration="",
    )


async def ask_question_to_api(question: str, config: dict) -> AskQuestionResponseBase:

    api_key: str = os.getenv("OPEN_API_KEY")

    stream: bool = config["llm"]["common"]["stream"]

    endpoint: str = config["llm"]["api"]["endpoint"]
    model: str = config["llm"]["api"]["model"]
    max_output_tokens: int = config["llm"]["api"]["max_output_tokens"]
    max_prompt_chars = config["llm"]["api"]["max_prompt_chars"]

    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks(embeded_question)

    prompt: list[dict[str, str]] = build_prompt(
        question, retrieved_chunks, max_prompt_chars
    )

    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "stream": stream,
        "max_output_tokens": max_output_tokens,
    }

    llm_response = await ask_question_to_api_client(payload, endpoint, api_key)

    sources: dict[str, int] = design_source(retrieved_chunks)

    cost: float = calculate_cost(llm_response)

    return AskQuestionResponseBase(
        llm_response=llm_response["output"][1]["content"][0]["text"],
        retrieved_chunks=retrieved_chunks,
        retrieved_documents=sources,
        model=model,
        generated_prompt=prompt,
        duration="",
        input_tokens=llm_response["usage"]["input_tokens"],
        output_tokens=llm_response["usage"]["output_tokens"],
        total_tokens=llm_response["usage"]["total_tokens"],
        cost=cost,
    )


def design_source(retrieved_chunks: list[dict[str, Any]]) -> dict[str, int]:
    sources: dict[str, int] = {}

    for chunk in retrieved_chunks:
        title = chunk["metadata"]["title"]

        if title in sources:
            sources[title] += 1
        else:
            sources[title] = 1

    sources_sorted = dict(
        sorted(sources.items(), key=lambda item: item[1], reverse=True)
    )

    return sources_sorted


def calculate_cost(llm_response) -> float:

    # Tarification gpt-5-mini
    input_price = 0.250
    output_price = 2

    input_tokens = llm_response["usage"]["input_tokens"]
    output_tokens = llm_response["usage"]["output_tokens"]

    cost = input_tokens * input_price / 1000000 + output_tokens * output_price / 1000000

    cost *= 0.86  # USD -> EUR le 04/03/2026

    return round(cost, 4)
