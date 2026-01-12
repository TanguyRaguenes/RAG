from typing import Any

from app.dal.clients.embedder_client import embed_question
from app.dal.clients.llm_client import ask_question_to_llm
from app.dal.clients.retriever_client import retrieve_chunks
from app.domain.models.ask_question_response_model import AskQuestionResponseBase
from app.services.prompt_builder_service import build_message


async def ask_question(question: str, config: dict) -> AskQuestionResponseBase:
    base_url: str = config["llm"]["url_provider"]
    model: str = config["llm"]["model"]
    timeout_seconds: int = config["llm"]["timeout_seconds"]
    temperature: float = config["llm"]["temperature"]
    stream: bool = config["llm"]["stream"]
    max_tokens: int = config["llm"]["max_tokens"]

    embeded_question: list[float] = await embed_question(question)
    retrieved_chunks: list[dict[str, Any]] = await retrieve_chunks(embeded_question)

    if not retrieved_chunks:
        return "Je ne sais pas."

    message: list[dict[str, str]] = build_message(question, retrieved_chunks, config)

    payload: dict[str, Any] = {
        "model": model,
        "messages": message,
        "temperature": temperature,
        "stream": stream,
        "max_tokens": max_tokens,
    }

    llm_response = await ask_question_to_llm(payload, timeout_seconds, base_url)

    sources: list[str] = []
    for chunk in retrieved_chunks:
        sources.append(chunk["metadata"]["path"])

    sources = list(set(sources))

    response: AskQuestionResponseBase = {
        "llm_answer": llm_response["choices"][0]["message"]["content"],
        "sources": sources,
        "chunks": retrieved_chunks,
    }

    return response
