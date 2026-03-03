import os
from typing import Any

from app.dal.clients.embedder_client import embed_question
from app.dal.clients.llm_client import ask_question_to_api_openai, ask_question_to_llm
from app.dal.clients.retriever_client import retrieve_chunks
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.services.prompt_builder_service import build_prompt


async def ask_question(question: str, config: dict) -> AskQuestionResponseBase:
    url: str = config["llm"]["url"]
    model: str = config["llm"]["model"]
    timeout_seconds: int = config["llm"]["timeout_seconds"]
    temperature: float = config["llm"]["temperature"]
    stream: bool = config["llm"]["stream"]
    max_tokens: int = config["llm"]["max_tokens"]
    num_ctx: int = config["llm"]["num_ctx"]

    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks(embeded_question)

    prompt: list[dict[str, str]] = build_prompt(question, retrieved_chunks, config)

    payload: dict[str, Any] = {
        "model": model,
        "messages": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }

    llm_response = await ask_question_to_llm(payload, timeout_seconds, url)

    sources: dict[str, int] = design_source(retrieved_chunks)

    return AskQuestionResponseBase(
        llm_response=llm_response["choices"][0]["message"]["content"],
        retrieved_chunks=retrieved_chunks,
        retrieved_documents=sources,
        model=model,
        generated_prompt=prompt,
        duration="",
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


async def ask_question_api_openai(
    question: str, config: dict
) -> AskQuestionResponseBase:
    api_key: str = os.getenv("OPEN_API_KEY")

    url: str = "https://api.openai.com/v1/chat/completions"
    model: str = "gpt-4o"
    timeout_seconds: int = config["llm"]["timeout_seconds"]
    temperature: float = config["llm"]["temperature"]
    stream: bool = config["llm"]["stream"]
    max_tokens: int = config["llm"]["max_tokens"]

    embeded_question: list[float] = await embed_question(question)

    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks(embeded_question)

    prompt: list[dict[str, str]] = build_prompt(question, retrieved_chunks, config)

    payload: dict[str, Any] = {
        "model": model,
        "messages": prompt,
        "stream": stream,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    llm_response = await ask_question_to_api_openai(
        payload, timeout_seconds, url, api_key
    )

    sources: dict[str, int] = design_source(retrieved_chunks)

    return AskQuestionResponseBase(
        llm_response=llm_response["choices"][0]["message"]["content"],
        retrieved_chunks=retrieved_chunks,
        retrieved_documents=sources,
        model=model,
        generated_prompt=prompt,
        duration="",
    )
