import os
from collections import Counter
from decimal import Decimal
from typing import Any, Protocol

import asyncpg
from opentelemetry import trace
from pydantic import ValidationError

from app.core.exceptions import DependencyResponseError
from app.core.metrics import (
    SERVICE_NAME,
    orchestrator_cost_total,
    orchestrator_tokens_total,
    rag_cost_eur_total,
    rag_tokens_total,
)
from app.dal.clients.llm_client import ask_question_to_api as ask_question_to_api_client
from app.dal.clients.llm_client import ask_question_to_llm as ask_question_to_llm_client
from app.dal.repositories.usage_repository import UsageRepository
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.schemas.llm_response_schema import (
    ApiLlmResponse,
    ApiLlmUsage,
    LocalLlmResponse,
)
from app.services.prompt_builder_service import build_prompt
from app.services.retrieve_chunks_service import retrieve_and_rerank_chunks

tracer = trace.get_tracer(__name__)


class ModelPricingRepositoryProtocol(Protocol):
    """Contrat de lecture du tarif actif utilisé avant un appel LLM payant."""

    async def get_active_model_pricing(
        self,
        *,
        provider: str,
        model_name: str,
    ) -> tuple[Decimal, Decimal]:
        """Retourne les tarifs input et output par million de tokens.

        Args:
            provider: Fournisseur LLM associé au tarif actif.
            model_name: Nom stable du modèle facturé.

        Returns:
            Prix d'entrée et de sortie par million de tokens.
        """
        ...


async def ask_question_to_local_model(
    question: str, config: dict[str, Any]
) -> AskQuestionResponseBase:
    """Pose une question au modèle local après récupération du contexte.

    Args:
        question: Question utilisateur, jamais loggée telle quelle.
        config: Configuration applicative contenant LLM, retrieval et prompt.

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
            question, config
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
    db_pool: asyncpg.Pool,
) -> AskQuestionResponseBase:
    """Pose une question à une API LLM externe après récupération du contexte.

    Args:
        question: Question utilisateur, jamais loggée telle quelle.
        config: Configuration applicative contenant LLM, retrieval et prompt.
        db_pool: Pool PostgreSQL utilisé pour récupérer le tarif du modèle.

    Returns:
        Réponse RAG enrichie avec tokens et coût estimé.

    Raises:
        KeyError: Si une clé attendue de configuration ou de réponse LLM manque.
        ApplicationError: Si le retrieval, reranking, LLM ou tarif modèle échoue.
    """
    with tracer.start_as_current_span("orchestrator.ask_api_model") as span:
        api_key: str | None = os.getenv("OPEN_API_KEY")

        stream: bool = config["llm"]["common"]["stream"]

        provider: str = config["llm"]["api"]["provider"]
        endpoint: str = config["llm"]["api"]["endpoint"]
        model: str = config["llm"]["api"]["model"]
        max_output_tokens: int = config["llm"]["api"]["max_output_tokens"]
        max_prompt_chars = config["llm"]["api"]["max_prompt_chars"]
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)

        retrieved_chunks: list[dict[str, Any]] = await retrieve_and_rerank_chunks(
            question, config
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

        pricing_repository: ModelPricingRepositoryProtocol = UsageRepository(db_pool)
        input_price, output_price = await pricing_repository.get_active_model_pricing(
            provider=provider,
            model_name=model,
        )

        raw_llm_response = await ask_question_to_api_client(payload, endpoint, api_key)
        llm_response = _validate_api_llm_response(raw_llm_response)

        sources: dict[str, int] = design_source(retrieved_chunks)

        cost = calculate_cost(
            usage=llm_response.usage,
            input_price=input_price,
            output_price=output_price,
        )
        _record_llm_usage(provider, model, llm_response, cost)

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
            cost=cost,
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


def calculate_cost(
    *,
    usage: ApiLlmUsage,
    input_price: Decimal,
    output_price: Decimal,
) -> float:
    """Calcule le coût estimé d'un appel LLM API.

    Args:
        usage: Compteurs de tokens validés de la réponse LLM.
        input_price: Prix d'un million de tokens d'entrée.
        output_price: Prix d'un million de tokens de sortie.

    Returns:
        Coût estimé arrondi à six décimales.

    """
    input_tokens = Decimal(usage.input_tokens)
    output_tokens = Decimal(usage.output_tokens)

    cost = input_tokens * input_price / Decimal(
        1000000
    ) + output_tokens * output_price / Decimal(1000000)

    return float(cost.quantize(Decimal("0.000001")))


def _record_llm_usage(
    provider: str,
    model: str,
    llm_response: ApiLlmResponse,
    cost: float,
) -> None:
    """Enregistre les métriques de tokens et de coût LLM.

    Args:
        provider: Provider LLM à faible cardinalité.
        model: Modèle LLM utilisé.
        llm_response: Réponse LLM validée contenant les compteurs d'usage.
        cost: Coût estimé de l'appel.

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
    orchestrator_cost_total.labels(provider=provider, model=model).inc(cost)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="input"
    ).inc(usage.input_tokens)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="output"
    ).inc(usage.output_tokens)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="total"
    ).inc(usage.total_tokens)
    rag_cost_eur_total.labels(service=SERVICE_NAME, provider=provider, model=model).inc(
        cost
    )


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
        Réponse typée prête pour extraction et calcul de coût.

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
