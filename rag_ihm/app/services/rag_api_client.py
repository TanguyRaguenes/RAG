import os
import logging
from datetime import date
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


class RagApiError(Exception):
    """Erreur affichable côté IHM sans exposer de données sensibles."""

    def __init__(self, user_message: str, details: dict[str, Any] | None = None):
        """Initialise une erreur affichable côté IHM.

        Args:
            user_message: Message destiné à l'utilisateur.
            details: Détails techniques non sensibles pour diagnostic.

        Returns:
            Aucune valeur.
        """
        self.user_message = user_message
        self.details = details or {}
        super().__init__(user_message)


@dataclass(frozen=True)
class ChatApiConfig:
    """Configuration des appels IHM vers l'orchestrator."""

    health_url: str
    ask_question_url: str


@dataclass(frozen=True)
class EvaluatorApiConfig:
    """Configuration des appels IHM vers l'evaluator."""

    health_url: str
    evaluate_url: str


def load_chat_api_config() -> ChatApiConfig:
    """Charge la configuration du client orchestrator.

    Returns:
        Configuration des endpoints de chat.

    Raises:
        RagApiError: Si une variable obligatoire manque.
    """
    return ChatApiConfig(
        health_url=_required_env("RAG_ORCHESTRATOR_TEST_CONNEXION_URL"),
        ask_question_url=_required_env("RAG_ORCHESTRATOR_ASK_QUESTION_URL"),
    )


def load_evaluator_api_config() -> EvaluatorApiConfig:
    """Charge la configuration du client evaluator.

    Returns:
        Configuration des endpoints d'évaluation.

    Raises:
        RagApiError: Si une variable obligatoire manque.
    """
    return EvaluatorApiConfig(
        health_url=_required_env("RAG_EVALUATOR_TEST_CONNEXION_URL"),
        evaluate_url=_required_env("RAG_EVALUATOR_EVALUATE_RAG_URL"),
    )


def check_api_health(base_url: str) -> None:
    """Vérifie qu'un service expose sa documentation FastAPI.

    Args:
        base_url: URL de base du service à vérifier.

    Returns:
        Aucune valeur.

    Raises:
        RagApiError: Si le service est indisponible ou retourne un statut non OK.
    """
    logger.info(
        "checking api health", extra={"service": "rag_ihm", "event": "api_health_check"}
    )
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
    """Envoie une question utilisateur à l'orchestrator.

    Args:
        config: Configuration des endpoints orchestrator.
        question: Question utilisateur, non loggée.
        provider: Provider LLM demandé.
        access_token: Token OIDC utilisateur.

    Returns:
        Réponse JSON de l'orchestrator.

    Raises:
        RagApiError: Si la session est absente, l'appel échoue ou la réponse est invalide.
    """
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
        raise RagApiError(
            "La demande n'a pas pu être envoyée au service RAG."
        ) from exception

    _raise_for_error_response(response)
    return _response_json(response)


def get_my_quota_usage(
    config: ChatApiConfig,
    access_token: str | None,
) -> dict[str, Any]:
    """Récupère le quota et la consommation de l'utilisateur connecté.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

    Returns:
        Données de quota de l'utilisateur connecté retournées par l'orchestrator.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    data = _authenticated_get(_usage_url(config, "/usage/quota/me"), access_token)

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def list_admin_quota_usages(
    config: ChatApiConfig,
    access_token: str | None,
) -> list[dict[str, Any]]:
    """Liste admin quota usages pour alimenter une réponse API ou un écran d'administration.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

    Returns:
        Liste des quotas utilisateur retournée pour l'écran d'administration.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    data = _authenticated_get(
        _usage_url(config, "/usage/quota/admin/users"), access_token
    )

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
    """Met à jour admin quota usage dans le stockage ou le service cible.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.
        max_tokens_par_mois: Plafond mensuel de tokens à appliquer à l'utilisateur.
        actif: Indique si la règle de quota utilisateur est active.

    Returns:
        Quota utilisateur mis à jour côté orchestrator.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
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
    """Liste les feedbacks d'interactions sur une période pour les administrateurs.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        start_date: Date de début du filtre de période.
        end_date: Date de fin du filtre de période.

    Returns:
        Feedbacks d'interactions prêts à être affichés dans l'IHM.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
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
    """Récupère les préférences d'affichage de l'utilisateur connecté.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

    Returns:
        Préférences utilisateur retournées par l'orchestrator.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    data = _authenticated_get(_usage_url(config, "/usage/preferences/me"), access_token)

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def update_my_preferences(
    config: ChatApiConfig,
    access_token: str | None,
    theme_preference: str,
) -> dict[str, Any]:
    """Met à jour la préférence de thème de l'utilisateur connecté.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        theme_preference: Préférence de thème choisie par l'utilisateur.

    Returns:
        Préférences utilisateur après mise à jour côté orchestrator.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
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
    """Envoie au backend la note et le commentaire saisis pour une réponse RAG.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        interaction_id: Identifiant de l'interaction RAG concernée.
        note: Note utilisateur associée au feedback.
        commentaire: Commentaire optionnel associé au feedback.

    Returns:
        Feedback enregistré par l'orchestrator pour l'interaction donnée.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    data = _authenticated_post(
        _usage_url(config, f"/usage/interactions/{interaction_id}/feedback"),
        access_token,
        {"note": note, "commentaire": commentaire},
    )

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def run_evaluation(config: EvaluatorApiConfig) -> dict[str, Any]:
    """Déclenche l'évaluation RAG auprès du service evaluator.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Résultat complet de l'évaluation RAG retourné par l'evaluator.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    try:
        response = requests.post(config.evaluate_url, timeout=300)
    except requests.exceptions.Timeout as exception:
        raise RagApiError(
            "L'évaluation prend trop de temps. Réessaie plus tard."
        ) from exception
    except requests.exceptions.ConnectionError as exception:
        raise RagApiError(
            "Le service d'évaluation est injoignable pour le moment."
        ) from exception
    except requests.RequestException as exception:
        raise RagApiError("L'évaluation n'a pas pu être lancée.") from exception

    _raise_for_error_response(response)
    return _response_json_any(response)


def _required_env(name: str) -> str:
    """Lit une variable d'environnement obligatoire pour l'IHM.

    Args:
        name: Nom de la variable à lire.

    Returns:
        Valeur de la variable.

    Raises:
        RagApiError: Si la variable est absente ou vide.
    """
    value = os.getenv(name)
    if not value:
        raise RagApiError(f"Configuration manquante : {name}.")
    return value


def _usage_url(config: ChatApiConfig, path: str) -> str:
    """Construit une URL usage à partir de l'endpoint ask_question.

    Args:
        config: Configuration des endpoints orchestrator.
        path: Chemin usage à ajouter.

    Returns:
        URL complète de l'endpoint usage.
    """
    base_url = config.ask_question_url.rsplit("/", 1)[0]

    return f"{base_url}{path}"


def _authenticated_get(
    url: str,
    access_token: str | None,
    params: dict[str, Any] | None = None,
):
    """Exécute une requête GET authentifiée vers l'orchestrator.

    Args:
        url: URL cible de l'appel HTTP.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        params: Paramètres de query string transmis à l'API appelée.

    Returns:
        Corps JSON décodé de la réponse GET authentifiée.
    """
    response = _authenticated_request(
        "GET",
        url,
        access_token,
        params=params,
    )
    return _response_json_any(response)


def _authenticated_post(url: str, access_token: str | None, payload: dict[str, Any]):
    """Exécute une requête POST authentifiée vers l'orchestrator.

    Args:
        url: URL cible de l'appel HTTP.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        payload: Corps JSON transmis à une API externe ou persisté en base.

    Returns:
        Corps JSON décodé de la réponse POST authentifiée.
    """
    response = _authenticated_request(
        "POST",
        url,
        access_token,
        payload=payload,
    )
    return _response_json_any(response)


def _response_json_any(response: requests.Response):
    """Décode une réponse JSON dont le type racine peut varier.

    Args:
        response: Réponse HTTP ou objet de réponse à décoder.

    Returns:
        Corps JSON décodé, quel que soit son type racine.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    try:
        return response.json()
    except ValueError as exception:
        raise RagApiError("Le service a retourné une réponse illisible.") from exception


def _authenticated_patch(url: str, access_token: str | None, payload: dict[str, Any]):
    """Exécute une requête PATCH authentifiée vers l'orchestrator.

    Args:
        url: URL cible de l'appel HTTP.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        payload: Corps JSON transmis à une API externe ou persisté en base.

    Returns:
        Corps JSON objet de la réponse PATCH authentifiée.
    """
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
    """Centralise l'envoi HTTP authentifié vers les APIs RAG.

    Args:
        method: Méthode HTTP utilisée pour l'appel authentifié.
        url: URL cible de l'appel HTTP.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        params: Paramètres de query string transmis à l'API appelée.
        payload: Corps JSON transmis à une API externe ou persisté en base.

    Returns:
        Réponse HTTP validée après authentification bearer.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
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
        raise RagApiError(
            "La demande n'a pas pu être envoyée au service RAG."
        ) from exception

    _raise_for_error_response(response)
    return response


def _auth_headers(access_token: str) -> dict[str, str]:
    """Construit l'en-tête Authorization à partir du token courant.

    Args:
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

    Returns:
        Dictionnaire d'en-têtes contenant le bearer token à transmettre à l'orchestrator.
    """
    return {"Authorization": f"Bearer {access_token}"}


def _docs_url(base_url: str) -> str:
    """Construit l'URL de documentation FastAPI utilisée pour les healthchecks.

    Args:
        base_url: URL de base utilisée pour construire un endpoint complet.

    Returns:
        URL terminée par `/docs`, utilisée pour ouvrir la documentation ou tester le backend.
    """
    clean_url = base_url.rstrip("/")
    if clean_url.endswith("/docs"):
        return clean_url
    return f"{clean_url}/docs"


def _raise_for_error_response(response: requests.Response) -> None:
    """Transforme une réponse HTTP non OK en erreur affichable côté IHM.

    Args:
        response: Réponse HTTP ou objet de réponse à décoder.

    Raises:
        RagApiError: Si l'API appelée par l'IHM est indisponible ou retourne une réponse inexploitable.
    """
    if response.status_code == 200:
        return

    details = _safe_response_details(response)
    raise RagApiError(_extract_error_message(details), details=details)


def _response_json(response: requests.Response) -> dict[str, Any]:
    """Décode une réponse JSON dictionnaire.

    Args:
        response: Réponse HTTP `requests`.

    Returns:
        Corps JSON sous forme de dictionnaire.

    Raises:
        RagApiError: Si le JSON est invalide ou n'est pas un objet.
    """
    try:
        data = response.json()
    except ValueError as exception:
        raise RagApiError("Le service a retourné une réponse illisible.") from exception

    if not isinstance(data, dict):
        raise RagApiError("Le service a retourné un format inattendu.")

    return data


def _safe_response_details(response: requests.Response) -> dict[str, Any]:
    """Extrait des détails de réponse sans lever d'erreur de parsing.

    Args:
        response: Réponse HTTP `requests`.

    Returns:
        Détails JSON ou texte tronqué.
    """
    try:
        data = response.json()
    except ValueError:
        data = {"response_text": _truncate(response.text)}

    if isinstance(data, dict):
        return data
    return {"response": data}


def _extract_error_message(details: dict[str, Any]) -> str:
    """Extrait le message d'erreur le plus utile depuis une réponse backend.

    Args:
        details: Informations non sensibles ajoutées à la réponse d'erreur pour faciliter le diagnostic.

    Returns:
        Message d'erreur le plus pertinent à afficher à l'utilisateur.
    """
    original_exception = details.get("original_exception")
    if isinstance(original_exception, dict) and original_exception.get("message"):
        return str(original_exception["message"])

    for key in ("message", "detail", "error"):
        value = details.get(key)
        if value:
            return str(value)

    return "Le service RAG a retourné une erreur."


def _truncate(value: str, limit: int = 1000) -> str:
    """Tronque une chaîne pour éviter d'afficher une réponse technique trop longue.

    Args:
        value: Valeur à convertir, borner ou formater.
        limit: Nombre maximal de caractères conservés.

    Returns:
        Chaîne d'origine ou version tronquée avec points de suspension.
    """
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}..."
