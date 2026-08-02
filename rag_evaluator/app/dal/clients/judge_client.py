import os
import time
from collections.abc import Callable
from typing import Protocol

import httpx
from opentelemetry import trace
from pydantic import ValidationError

from app.core.config import EvaluatorConfig
from app.core.exceptions import EvaluatorClientError
from app.core.metrics import (
    evaluator_errors_total,
    evaluator_external_call_duration_seconds,
)
from app.domain.models.judge_response_model import JudgeOutput
from app.schemas.judge_schema import (
    ChatCompletionResponse,
    JudgeMessage,
    ResponsesApiResponse,
)

tracer = trace.get_tracer(__name__)


class JudgeClient(Protocol):
    """Contrat métier minimal d'un fournisseur de jugement externe."""

    async def judge(self, messages: list[JudgeMessage]) -> str:
        """Demande un jugement au fournisseur.

        Args:
            messages: Prompt structuré à transmettre au modèle de jugement.

        Returns:
            Contenu textuel non vide du premier choix du modèle.

        Raises:
            EvaluatorClientError: Si le fournisseur ou son contrat HTTP échoue.
        """
        ...


class OpenAIJudgeClient:
    """Client du contrat OpenAI `POST /v1/responses`."""

    def __init__(self, config: EvaluatorConfig, api_key: str | None) -> None:
        """Configure le transport OpenAI.

        Args:
            config: Paramètres de génération et timeout validés au démarrage.
            api_key: Clé d'API lue depuis l'environnement, jamais journalisée.
        """
        self._config = config
        self._api_key = api_key

    async def judge(self, messages: list[JudgeMessage]) -> str:
        """Envoie un prompt selon le contrat chat completions OpenAI.

        Args:
            messages: Messages système et utilisateur du jugement.

        Returns:
            Contenu du premier choix OpenAI.

        Raises:
            EvaluatorClientError: Si l'appel ou la réponse OpenAI est invalide.
        """
        llm = self._config.llm
        payload: dict[str, object] = {
            "model": llm.api.model,
            "input": [message.model_dump() for message in messages],
            "stream": llm.common.stream,
            "max_output_tokens": llm.api.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "rag_judge_evaluation",
                    "strict": True,
                    "schema": JudgeOutput.model_json_schema(),
                }
            },
        }
        return await _post_json(
            url=llm.api.endpoint,
            payload=payload,
            timeout_seconds=llm.common.timeout_seconds,
            headers=_build_auth_headers(self._api_key),
            response_parser=_parse_responses_api_content,
        )


class LocalJudgeClient:
    """Client d'un serveur local compatible OpenAI chat completions."""

    def __init__(self, config: EvaluatorConfig) -> None:
        """Configure le transport du juge local.

        Args:
            config: URL, modèle et paramètres validés du juge local.
        """
        self._config = config

    async def judge(self, messages: list[JudgeMessage]) -> str:
        """Envoie le prompt au endpoint chat completions local.

        Args:
            messages: Messages système et utilisateur du jugement.

        Returns:
            Contenu du premier choix du modèle local.

        Raises:
            EvaluatorClientError: Si l'appel ou la réponse locale est invalide.
        """
        llm = self._config.llm
        payload: dict[str, object] = {
            "model": llm.local.model,
            "messages": [message.model_dump() for message in messages],
            "temperature": llm.common.temperature,
            "max_tokens": llm.local.max_output_tokens,
            "stream": llm.common.stream,
        }
        return await _post_json(
            url=llm.local.endpoint,
            payload=payload,
            timeout_seconds=llm.common.timeout_seconds,
            response_parser=_parse_chat_completion_content,
        )


class ConfiguredJudgeClient:
    """Sélectionne une implémentation du juge à partir de la configuration."""

    def __init__(self, delegate: JudgeClient) -> None:
        """Injecte le client concret sélectionné.

        Args:
            delegate: Client OpenAI ou local respectant le contrat `JudgeClient`.
        """
        self._delegate = delegate

    @classmethod
    def from_config(cls, config: EvaluatorConfig) -> "ConfiguredJudgeClient":
        """Construit le client correspondant à la méthode d'évaluation.

        Args:
            config: Configuration typée contenant le choix du fournisseur.

        Returns:
            Façade de jugement prête à être injectée dans le service métier.
        """
        if config.judge_provider == "api":
            delegate: JudgeClient = OpenAIJudgeClient(
                config=config,
                api_key=os.getenv("OPEN_API_KEY"),
            )
        else:
            delegate = LocalJudgeClient(config=config)
        return cls(delegate)

    async def judge(self, messages: list[JudgeMessage]) -> str:
        """Délègue le jugement au fournisseur configuré.

        Args:
            messages: Prompt structuré à transmettre au juge.

        Returns:
            Contenu textuel validé du jugement.

        Raises:
            EvaluatorClientError: Si le fournisseur externe échoue.
        """
        return await self._delegate.judge(messages)


def _build_auth_headers(api_key: str | None) -> dict[str, str]:
    """Construit les headers d'authentification du fournisseur OpenAI.

    Args:
        api_key: Clé API optionnelle lue depuis l'environnement.

    Returns:
        Headers JSON avec bearer token lorsqu'il est disponible.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _parse_chat_completion_content(data: object) -> str:
    """Valide la réponse chat completions et extrait son contenu.

    Args:
        data: JSON brut retourné par le fournisseur.

    Returns:
        Contenu non vide du premier choix.

    Raises:
        EvaluatorClientError: Si la réponse ne respecte pas le contrat attendu.
    """
    try:
        response = ChatCompletionResponse.model_validate(data)
    except ValidationError as exception:
        raise EvaluatorClientError(
            message="Réponse du juge LLM invalide",
            details={"validation_errors": exception.error_count()},
        ) from exception
    return response.choices[0].message.content


def _parse_responses_api_content(data: object) -> str:
    """Valide une réponse de l'API Responses et extrait son premier texte.

    Args:
        data: JSON brut retourné par le fournisseur externe.

    Returns:
        Premier contenu textuel non vide de la réponse.

    Raises:
        EvaluatorClientError: Si la réponse ne respecte pas le contrat attendu.
    """
    try:
        response = ResponsesApiResponse.model_validate(data)
    except ValidationError as exception:
        raise EvaluatorClientError(
            message="Réponse du juge LLM invalide",
            details={"validation_errors": exception.error_count()},
        ) from exception

    for output in response.output:
        for content in output.content:
            if content.text and content.text.strip():
                return content.text

    raise EvaluatorClientError(message="Réponse du juge LLM invalide")


async def _post_json(
    *,
    url: str,
    payload: dict[str, object],
    timeout_seconds: float,
    response_parser: Callable[[object], str],
    headers: dict[str, str] | None = None,
) -> str:
    """Exécute l'appel HTTP instrumenté vers le juge.

    Args:
        url: Endpoint chat completions cible.
        payload: Corps JSON conforme au fournisseur sélectionné.
        timeout_seconds: Délai maximal validé de l'appel.
        response_parser: Fonction validant et extrayant le texte du fournisseur.
        headers: Headers HTTP optionnels, dont l'authentification OpenAI.

    Returns:
        Contenu non vide validé par le schéma chat completions.

    Raises:
        EvaluatorClientError: Si le transport, le statut ou le JSON échoue.
    """
    start = time.perf_counter()
    try:
        with tracer.start_as_current_span("evaluator.call_judge"):
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
    except httpx.HTTPStatusError as exception:
        _record_external_error("judge", "judge", "http_status", start)
        raise EvaluatorClientError(
            message="Le juge LLM a refusé la requête",
            details={"status_code": exception.response.status_code},
        ) from exception
    except httpx.ConnectError as exception:
        _record_external_error("judge", "judge", "connect_error", start)
        raise EvaluatorClientError(
            message="Impossible de se connecter au juge LLM"
        ) from exception
    except httpx.TimeoutException as exception:
        _record_external_error("judge", "judge", "timeout", start)
        raise EvaluatorClientError(
            message="Timeout lors de l'appel au juge LLM"
        ) from exception
    except httpx.RequestError as exception:
        _record_external_error("judge", "judge", "request_error", start)
        raise EvaluatorClientError(
            message="Erreur réseau lors de l'appel au juge LLM"
        ) from exception
    except ValueError as exception:
        _record_external_error("judge", "judge", "invalid_json", start)
        raise EvaluatorClientError(
            message="Le juge LLM a retourné une réponse JSON invalide"
        ) from exception

    try:
        content = response_parser(data)
    except EvaluatorClientError:
        _record_external_error("judge", "judge", "invalid_format", start)
        raise

    evaluator_external_call_duration_seconds.labels(
        dependency="judge", operation="judge", status="success"
    ).observe(time.perf_counter() - start)
    return content


def _record_external_error(
    dependency: str, operation: str, error_type: str, start: float
) -> None:
    """Enregistre une erreur d'appel externe sans donnée à forte cardinalité.

    Args:
        dependency: Nom stable de la dépendance appelée.
        operation: Nom stable de l'opération appelée.
        error_type: Type technique stable de l'erreur.
        start: Instant initial utilisé pour calculer la durée.
    """
    evaluator_errors_total.labels(operation=operation, error_type=error_type).inc()
    evaluator_external_call_duration_seconds.labels(
        dependency=dependency, operation=operation, status="error"
    ).observe(time.perf_counter() - start)
