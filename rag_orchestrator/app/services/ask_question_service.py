import os
from collections import Counter
from typing import Any, Literal

from opentelemetry import trace
from pydantic import ValidationError

from app.core.exceptions import DependencyResponseError
from app.core.metrics import (
    SERVICE_NAME,
    orchestrator_tokens_total,
    rag_tokens_total,
)
from app.dal.clients.llm_client import ask_question_to_api as ask_question_to_api_client
from app.dal.clients.llm_client import ask_question_to_llm as ask_question_to_llm_client
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.llm_response_schema import (
    ApiLlmResponse,
    LocalLlmResponse,
)
from app.services.prompt_builder_service import build_prompt
from app.services.retrieve_chunks_service import retrieve_and_rerank_chunks

tracer = trace.get_tracer(__name__)


async def ask_question_to_local_model(
    question: str,
    config: dict[str, Any],
    collection_profile: Literal["default", "evaluation"] = "default",
) -> AskQuestionResponseBase:
    """Pose une question au modèle local après récupération du contexte.

    Args:
        question: Question utilisateur, jamais loggée telle quelle.
        config: Configuration applicative contenant LLM, retrieval et prompt.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Réponse RAG construite à partir du LLM local et des chunks récupérés.

    Raises:
        KeyError: Si une clé attendue de configuration ou de réponse LLM manque.
        ApplicationError: Si le retrieval, reranking ou LLM local échoue.
    """
    with tracer.start_as_current_span("orchestrator.ask_local_model") as span:
        span.set_attribute("llm.provider", "local")

        timeout_seconds: int = config["llm"]["common"]["timeout_seconds"]
        temperature: float = config["llm"]["common"]["temperature"]
        stream: bool = config["llm"]["common"]["stream"]

        endpoint: str = config["llm"]["local"]["endpoint"]
        model: str = config["llm"]["local"]["model"]
        max_output_tokens: int = config["llm"]["local"]["max_output_tokens"]
        context_window_tokens: int = config["llm"]["local"]["context_window_tokens"]
        max_prompt_chars = config["llm"]["local"]["max_prompt_chars"]
        span.set_attribute("llm.model", model)

        retrieved_chunks: list[dict[str, Any]] = await retrieve_and_rerank_chunks(
            question, config, collection_profile
        )

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

        raw_llm_response = await ask_question_to_llm_client(
            payload, timeout_seconds, endpoint
        )
        llm_response = _validate_local_llm_response(raw_llm_response)

        sources: dict[str, int] = design_source(retrieved_chunks)

        return AskQuestionResponseBase(
            llm_response=llm_response.choices[0].message.content,
            retrieved_chunks=retrieved_chunks,
            retrieved_documents=sources,
            model=model,
            generated_prompt=prompt,
            duration="",
        )


async def ask_question_to_api(
    question: str,
    config: dict[str, Any],
    collection_profile: Literal["default", "evaluation"] = "default",
) -> AskQuestionResponseBase:
    """Pose une question à une API LLM externe après récupération du contexte.

    Args:
        question: Question utilisateur, jamais loggée telle quelle.
        config: Configuration applicative contenant LLM, retrieval et prompt.
        collection_profile: Profil fixe de collection à interroger.

    Returns:
        Réponse RAG enrichie avec les compteurs de tokens.

    Raises:
        KeyError: Si une clé attendue de configuration ou de réponse LLM manque.
        ApplicationError: Si le retrieval, reranking ou LLM échoue.
    """
    with tracer.start_as_current_span("orchestrator.ask_api_model") as span:
        api_key: str | None = os.getenv("OPEN_API_KEY")

        timeout_seconds: int = config["llm"]["common"]["timeout_seconds"]
        stream: bool = config["llm"]["common"]["stream"]

        provider: str = config["llm"]["api"]["provider"]
        endpoint: str = config["llm"]["api"]["endpoint"]
        model: str = config["llm"]["api"]["model"]
        max_output_tokens: int = config["llm"]["api"]["max_output_tokens"]
        max_prompt_chars = config["llm"]["api"]["max_prompt_chars"]
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)

        retrieved_chunks: list[dict[str, Any]] = await retrieve_and_rerank_chunks(
            question, config, collection_profile
        )

        prompt: list[dict[str, str]] = build_prompt(
            question, retrieved_chunks, max_prompt_chars
        )

        payload: dict[str, Any] = {
            "model": model,
            "input": prompt,
            "stream": stream,
            "max_output_tokens": max_output_tokens,
        }

        raw_llm_response = await ask_question_to_api_client(
            payload, endpoint, api_key, timeout_seconds
        )
        llm_response = _validate_api_llm_response(raw_llm_response)

        sources: dict[str, int] = design_source(retrieved_chunks)

        _record_llm_usage(provider, model, llm_response)

        return AskQuestionResponseBase(
            llm_response=_extract_api_response_text(llm_response),
            retrieved_chunks=retrieved_chunks,
            retrieved_documents=sources,
            model=model,
            generated_prompt=prompt,
            duration="",
            input_tokens=llm_response.usage.input_tokens,
            output_tokens=llm_response.usage.output_tokens,
            total_tokens=llm_response.usage.total_tokens,
        )


def design_source(retrieved_chunks: list[dict[str, Any]]) -> dict[str, int]:
    """Agrège les sources documentaires des chunks récupérés.

    Args:
        retrieved_chunks: Chunks RAG contenant une métadonnée `title`.

    Returns:
        Dictionnaire `titre -> nombre de chunks`, trié par fréquence décroissante.

    Raises:
        DependencyResponseError: Si un chunk ne contient pas `metadata.title`.
    """
    try:
        sources = Counter(chunk["metadata"]["title"] for chunk in retrieved_chunks)
    except (KeyError, TypeError) as exception:
        raise DependencyResponseError(
            "Retrieved chunk metadata is malformed",
            details={"dependency": "retriever", "operation": "retrieve_chunks"},
        ) from exception

    return dict(sources.most_common())


def _record_llm_usage(
    provider: str,
    model: str,
    llm_response: ApiLlmResponse,
) -> None:
    """Enregistre les métriques de tokens LLM.

    Args:
        provider: Provider LLM à faible cardinalité.
        model: Modèle LLM utilisé.
        llm_response: Réponse LLM validée contenant les compteurs d'usage.
    """
    usage = llm_response.usage
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="input"
    ).inc(usage.input_tokens)
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="output"
    ).inc(usage.output_tokens)
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="total"
    ).inc(usage.total_tokens)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="input"
    ).inc(usage.input_tokens)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="output"
    ).inc(usage.output_tokens)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="total"
    ).inc(usage.total_tokens)


def _validate_local_llm_response(response: dict[str, Any]) -> LocalLlmResponse:
    """Valide la structure minimale d'une réponse de chat completion locale.

    Args:
        response: JSON brut retourné par le client LLM local.

    Returns:
        Réponse typée contenant au moins un message non vide.

    Raises:
        DependencyResponseError: Si la réponse ne respecte pas le contrat minimal attendu.
    """
    try:
        return LocalLlmResponse.model_validate(response)
    except ValidationError as exception:
        raise DependencyResponseError(
            "Local LLM response schema is invalid",
            details={"dependency": "llm", "operation": "local_llm"},
        ) from exception


def _validate_api_llm_response(response: dict[str, Any]) -> ApiLlmResponse:
    """Valide la sortie et les compteurs d'une réponse LLM externe.

    Args:
        response: JSON brut retourné par le client d'API LLM.

    Returns:
        Réponse typée prête pour l'extraction du texte et des compteurs de tokens.

    Raises:
        DependencyResponseError: Si la réponse ne respecte pas le contrat minimal attendu.
    """
    try:
        return ApiLlmResponse.model_validate(response)
    except ValidationError as exception:
        raise DependencyResponseError(
            "LLM API response schema is invalid",
            details={"dependency": "llm", "operation": "api_llm"},
        ) from exception


def _extract_api_response_text(response: ApiLlmResponse) -> str:
    """Recherche le texte généré par son type plutôt que par sa position.

    Args:
        response: Réponse LLM externe préalablement validée.

    Returns:
        Premier texte `output_text` non vide, avec repli sur un contenu textuel non typé.

    Raises:
        DependencyResponseError: Si aucun texte généré n'est présent dans la réponse.
    """
    message_outputs = [item for item in response.output if item.type == "message"]
    other_outputs = [item for item in response.output if item.type != "message"]

    for output in [*message_outputs, *other_outputs]:
        typed_contents = [item for item in output.content if item.type == "output_text"]
        other_contents = [item for item in output.content if item.type != "output_text"]
        for content in [*typed_contents, *other_contents]:
            if content.text and content.text.strip():
                return content.text

    raise DependencyResponseError(
        "LLM API response is missing output text",
        details={"dependency": "llm", "operation": "api_llm"},
    )
