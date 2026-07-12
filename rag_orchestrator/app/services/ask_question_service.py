import os
from collections import Counter
from decimal import Decimal
from typing import Any

import asyncpg
from opentelemetry import trace

from app.dal.clients.llm_client import ask_question_to_api as ask_question_to_api_client
from app.dal.clients.llm_client import ask_question_to_llm as ask_question_to_llm_client
from app.dal.repositories.usage_repository import UsageRepository
from app.core.metrics import (
    SERVICE_NAME,
    orchestrator_cost_total,
    rag_cost_eur_total,
    orchestrator_tokens_total,
    rag_cost_usd_total,
    rag_tokens_total,
)
from app.schemas.ask_question_response_schema import AskQuestionResponseBase
from app.services.prompt_builder_service import build_prompt
from app.services.retrieve_chunks_service import retrieve_and_rerank_chunks

tracer = trace.get_tracer(__name__)


async def ask_question_to_local_model(
    question: str, config: dict
) -> AskQuestionResponseBase:
    """Pose une question au modèle local après récupération du contexte.

    Args:
        question: Question utilisateur, jamais loggée telle quelle.
        config: Configuration applicative contenant LLM, retrieval et prompt.

    Returns:
        Réponse RAG construite à partir du LLM local et des chunks récupérés.

    Raises:
        KeyError: Si une clé attendue de configuration ou de réponse LLM manque.
        OrchestratorContainerCustomException: Si le retrieval, reranking ou LLM local échoue.
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

        llm_response = await ask_question_to_llm_client(
            payload, timeout_seconds, endpoint
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


async def ask_question_to_api(
    question: str,
    config: dict,
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
        OrchestratorContainerCustomException: Si le retrieval, reranking ou LLM externe échoue.
        asyncpg.PostgresError: Si la récupération du tarif modèle échoue.
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

        llm_response = await ask_question_to_api_client(payload, endpoint, api_key)

        sources: dict[str, int] = design_source(retrieved_chunks)

        cost: float = await calculate_cost(
            llm_response=llm_response,
            db_pool=db_pool,
            provider=provider,
            model=model,
        )
        _record_llm_usage(provider, model, llm_response, cost)

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
    """Agrège les sources documentaires des chunks récupérés.

    Args:
        retrieved_chunks: Chunks RAG contenant une métadonnée `title`.

    Returns:
        Dictionnaire `titre -> nombre de chunks`, trié par fréquence décroissante.

    Raises:
        KeyError: Si un chunk ne contient pas `metadata.title`.
    """
    sources = Counter(chunk["metadata"]["title"] for chunk in retrieved_chunks)

    return dict(sources.most_common())


async def calculate_cost(
    *,
    llm_response: dict[str, Any],
    db_pool: asyncpg.Pool,
    provider: str,
    model: str,
) -> float:
    """Calcule le coût estimé d'un appel LLM API.

    Args:
        llm_response: Réponse LLM contenant les tokens d'usage.
        db_pool: Pool PostgreSQL utilisé pour récupérer le prix actif.
        provider: Nom du provider LLM.
        model: Nom du modèle LLM.

    Returns:
        Coût estimé arrondi à six décimales.

    Raises:
        KeyError: Si les champs d'usage sont absents de la réponse LLM.
        asyncpg.PostgresError: Si la récupération du prix actif échoue.
    """
    usage_repository = UsageRepository(db_pool)
    input_price, output_price = await usage_repository.get_active_model_pricing(
        provider=provider,
        model_name=model,
    )

    input_tokens = Decimal(llm_response["usage"]["input_tokens"])
    output_tokens = Decimal(llm_response["usage"]["output_tokens"])

    cost = input_tokens * input_price / Decimal(
        "1000000"
    ) + output_tokens * output_price / Decimal("1000000")

    return float(cost.quantize(Decimal("0.000001")))


def _record_llm_usage(
    provider: str, model: str, llm_response: dict[str, Any], cost: float
) -> None:
    """Enregistre les métriques de tokens et de coût LLM.

    Args:
        provider: Provider LLM à faible cardinalité.
        model: Modèle LLM utilisé.
        llm_response: Réponse LLM contenant `usage`.
        cost: Coût estimé de l'appel.

    Returns:
        Aucune valeur.

    Raises:
        KeyError: Si la réponse LLM ne contient pas les champs `usage` attendus.
    """
    usage = llm_response["usage"]
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="input"
    ).inc(usage["input_tokens"])
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="output"
    ).inc(usage["output_tokens"])
    orchestrator_tokens_total.labels(
        provider=provider, model=model, token_type="total"
    ).inc(usage["total_tokens"])
    orchestrator_cost_total.labels(provider=provider, model=model).inc(cost)
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="input"
    ).inc(usage["input_tokens"])
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="output"
    ).inc(usage["output_tokens"])
    rag_tokens_total.labels(
        service=SERVICE_NAME, provider=provider, model=model, token_type="total"
    ).inc(usage["total_tokens"])
    rag_cost_usd_total.labels(service=SERVICE_NAME, provider=provider, model=model).inc(
        cost
    )
    rag_cost_eur_total.labels(service=SERVICE_NAME, provider=provider, model=model).inc(
        cost
    )
