import os
from dataclasses import dataclass
from typing import Any

import requests


class RagApiError(Exception):
    """Erreur affichable côté IHM sans exposer de données sensibles."""

    def __init__(self, user_message: str, details: dict[str, Any] | None = None):
        self.user_message = user_message
        self.details = details or {}
        super().__init__(user_message)


@dataclass(frozen=True)
class ChatApiConfig:
    health_url: str
    ask_question_url: str


@dataclass(frozen=True)
class EvaluatorApiConfig:
    health_url: str
    evaluate_url: str


def load_chat_api_config() -> ChatApiConfig:
    return ChatApiConfig(
        health_url=_required_env("RAG_ORCHESTRATOR_TEST_CONNEXION_URL"),
        ask_question_url=_required_env("RAG_ORCHESTRATOR_ASK_QUESTION_URL"),
    )


def load_evaluator_api_config() -> EvaluatorApiConfig:
    return EvaluatorApiConfig(
        health_url=_required_env("RAG_EVALUATOR_TEST_CONNEXION_URL"),
        evaluate_url=_required_env("RAG_EVALUATOR_EVALUATE_RAG_URL"),
    )


def check_api_health(base_url: str) -> None:
    url = _docs_url(base_url)
    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.Timeout as exception:
        raise RagApiError("Le service met trop de temps à répondre.") from exception
    except requests.exceptions.ConnectionError as exception:
        raise RagApiError("Le service est injoignable pour le moment.") from exception
    except requests.RequestException as exception:
        raise RagApiError("Impossible de vérifier l'état du service.") from exception

    if response.status_code != 200:
        raise RagApiError(
            f"Le service répond avec le code {response.status_code}.",
            details={
                "status_code": response.status_code,
                **_safe_response_details(response),
            },
        )


def ask_question(
    config: ChatApiConfig,
    question: str,
    provider: str,
    access_token: str | None,
) -> dict[str, Any]:
    if not access_token:
        raise RagApiError("La session a expiré. Reconnecte-toi pour continuer.")

    try:
        response = requests.post(
            config.ask_question_url,
            json={"question": question, "provider": provider, "channel": "streamlit"},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=360,
        )
    except requests.exceptions.Timeout as exception:
        raise RagApiError(
            "La réponse prend trop de temps. Réessaie dans quelques instants."
        ) from exception
    except requests.exceptions.ConnectionError as exception:
        raise RagApiError(
            "Le service de réponse est injoignable pour le moment."
        ) from exception
    except requests.RequestException as exception:
        raise RagApiError("La demande n'a pas pu être envoyée au service RAG.") from exception

    _raise_for_error_response(response)
    return _response_json(response)


def run_evaluation(config: EvaluatorApiConfig) -> dict[str, Any]:
    try:
        response = requests.post(config.evaluate_url, timeout=300)
    except requests.exceptions.Timeout as exception:
        raise RagApiError("L'évaluation prend trop de temps. Réessaie plus tard.") from exception
    except requests.exceptions.ConnectionError as exception:
        raise RagApiError("Le service d'évaluation est injoignable pour le moment.") from exception
    except requests.RequestException as exception:
        raise RagApiError("L'évaluation n'a pas pu être lancée.") from exception

    _raise_for_error_response(response)
    return _response_json(response)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RagApiError(f"Configuration manquante : {name}.")
    return value


def _docs_url(base_url: str) -> str:
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/docs"):
        return clean_url
    return f"{clean_url}/docs"


def _raise_for_error_response(response: requests.Response) -> None:
    if response.status_code == 200:
        return

    details = _safe_response_details(response)
    raise RagApiError(_extract_error_message(details), details=details)


def _response_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exception:
        raise RagApiError("Le service a retourné une réponse illisible.") from exception

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def _safe_response_details(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        data = {"response_text": _truncate(response.text)}

    if isinstance(data, dict):
        return data
    return {"response": data}


def _extract_error_message(details: dict[str, Any]) -> str:
    original_exception = details.get("original_exception")
    if isinstance(original_exception, dict) and original_exception.get("message"):
        return str(original_exception["message"])

    for key in ("message", "detail", "error"):
        value = details.get(key)
        if value:
            return str(value)

    return "Le service RAG a retourné une erreur."


def _truncate(value: str, limit: int = 1000) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}..."
