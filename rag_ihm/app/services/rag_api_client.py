import os
from datetime import date
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


def get_my_quota_usage(
    config: ChatApiConfig,
    access_token: str | None,
) -> dict[str, Any]:
    data = _authenticated_get(_usage_url(config, "/usage/quota/me"), access_token)

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def list_admin_quota_usages(
    config: ChatApiConfig,
    access_token: str | None,
) -> list[dict[str, Any]]:
    data = _authenticated_get(_usage_url(config, "/usage/quota/admin/users"), access_token)

    if not isinstance(data, list):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def update_admin_quota_usage(
    config: ChatApiConfig,
    access_token: str | None,
    user_id: str,
    max_tokens_par_mois: int,
    actif: bool,
) -> dict[str, Any]:
    url = _usage_url(config, f"/usage/quota/admin/users/{user_id}")

    data = _authenticated_patch(
        url,
        access_token,
        {"max_tokens_par_mois": max_tokens_par_mois, "actif": actif},
    )

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def list_admin_interaction_feedbacks(
    config: ChatApiConfig,
    access_token: str | None,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    data = _authenticated_get(
        _usage_url(config, "/usage/admin/interactions/feedbacks"),
        access_token,
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )

    if not isinstance(data, list):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def get_my_preferences(
    config: ChatApiConfig,
    access_token: str | None,
) -> dict[str, Any]:
    data = _authenticated_get(_usage_url(config, "/usage/preferences/me"), access_token)

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def update_my_preferences(
    config: ChatApiConfig,
    access_token: str | None,
    theme_preference: str,
) -> dict[str, Any]:
    data = _authenticated_patch(
        _usage_url(config, "/usage/preferences/me"),
        access_token,
        {"theme_preference": theme_preference},
    )

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def submit_interaction_feedback(
    config: ChatApiConfig,
    access_token: str | None,
    interaction_id: int,
    note: int,
    commentaire: str | None,
) -> dict[str, Any]:
    data = _authenticated_post(
        _usage_url(config, f"/usage/interactions/{interaction_id}/feedback"),
        access_token,
        {"note": note, "commentaire": commentaire},
    )

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


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
    return _response_json_any(response)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RagApiError(f"Configuration manquante : {name}.")
    return value


def _usage_url(config: ChatApiConfig, path: str) -> str:
    base_url = config.ask_question_url.rsplit("/", 1)[0]

    return f"{base_url}{path}"


def _authenticated_get(
    url: str,
    access_token: str | None,
    params: dict[str, Any] | None = None,
):
    response = _authenticated_request(
        "GET",
        url,
        access_token,
        params=params,
    )
    return _response_json_any(response)


def _authenticated_post(url: str, access_token: str | None, payload: dict[str, Any]):
    response = _authenticated_request(
        "POST",
        url,
        access_token,
        payload=payload,
    )
    return _response_json_any(response)


def _response_json_any(response: requests.Response):
    try:
        return response.json()
    except ValueError as exception:
        raise RagApiError("Le service a retourné une réponse illisible.") from exception


def _authenticated_patch(url: str, access_token: str | None, payload: dict[str, Any]):
    response = _authenticated_request(
        "PATCH",
        url,
        access_token,
        payload=payload,
    )
    return _response_json(response)


def _authenticated_request(
    method: str,
    url: str,
    access_token: str | None,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> requests.Response:
    if not access_token:
        raise RagApiError("La session a expiré. Reconnecte-toi pour continuer.")

    try:
        response = requests.request(
            method,
            url,
            params=params,
            json=payload,
            headers=_auth_headers(access_token),
            timeout=30,
        )
    except requests.exceptions.Timeout as exception:
        raise RagApiError("Le service met trop de temps à répondre.") from exception
    except requests.exceptions.ConnectionError as exception:
        raise RagApiError("Le service est injoignable pour le moment.") from exception
    except requests.RequestException as exception:
        raise RagApiError("La demande n'a pas pu être envoyée au service RAG.") from exception

    _raise_for_error_response(response)
    return response


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


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
