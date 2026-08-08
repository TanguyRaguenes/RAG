import logging
import os
from dataclasses import dataclass
from datetime import date
from typing import Any, cast
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import RagApiError
from app.dal.clients.http_client import HttpClientProtocol, RequestsHttpClient
from app.dal.clients.rag_client import RagClient
from app.schemas.api import (
    AdminInteractionFeedback,
    AskQuestionResponse,
    AuthenticatedUser,
    EvaluationResponse,
    FeedbackResponse,
    JsonValue,
    QuotaUsageResponse,
    ResponseContractError,
    validate_admin_feedback_list,
    validate_ask_question_response,
    validate_authenticated_user,
    validate_evaluation_response,
    validate_feedback_response,
    validate_quota_usage_list,
    validate_quota_usage_response,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatApiConfig:
    """Configuration des appels IHM vers l'orchestrator."""

    health_url: str
    ask_question_url: str

    @property
    def base_url(self) -> str:
        """Retourne la base orchestrator dérivée de l'endpoint de question.

        Returns:
            URL sans le segment final `/ask_question`, query string ni fragment.

        Raises:
            RagApiError: Si l'endpoint configuré n'est pas un endpoint de question.
        """
        parsed = urlsplit(self.ask_question_url)
        path = parsed.path.rstrip("/")
        if not path.endswith("/ask_question"):
            raise RagApiError(
                "L'URL de l'orchestrator est invalide.",
                details={"configuration": "RAG_ORCHESTRATOR_ASK_QUESTION_URL"},
            )
        base_path = path[: -len("/ask_question")].rstrip("/")
        return urlunsplit((parsed.scheme, parsed.netloc, base_path, "", "")).rstrip("/")


@dataclass(frozen=True)
class EvaluatorApiConfig:
    """Configuration des appels IHM vers l'evaluator."""

    health_url: str
    evaluate_url: str


def load_chat_api_config() -> ChatApiConfig:
    """Charge la configuration des endpoints orchestrator.

    Returns:
        Configuration immuable des endpoints de chat.

    Raises:
        RagApiError: Si une variable obligatoire manque.
    """
    return ChatApiConfig(
        health_url=_required_env("RAG_ORCHESTRATOR_TEST_CONNEXION_URL"),
        ask_question_url=_required_env("RAG_ORCHESTRATOR_ASK_QUESTION_URL"),
    )


def load_evaluator_api_config() -> EvaluatorApiConfig:
    """Charge la configuration des endpoints evaluator.

    Returns:
        Configuration immuable des endpoints d'évaluation.

    Raises:
        RagApiError: Si une variable obligatoire manque.
    """
    return EvaluatorApiConfig(
        health_url=_required_env("RAG_EVALUATOR_TEST_CONNEXION_URL"),
        evaluate_url=_required_env("RAG_EVALUATOR_EVALUATE_RAG_URL"),
    )


def create_rag_client(http_client: HttpClientProtocol | None = None) -> RagClient:
    """Crée le client externe en permettant l'injection du transport.

    Args:
        http_client: Transport alternatif utilisé notamment par les tests.

    Returns:
        Client des APIs RAG prêt à être utilisé par les services.
    """
    return RagClient(http_client or RequestsHttpClient())


def check_api_health(health_url: str, client: RagClient | None = None) -> None:
    """Vérifie l'URL de santé explicite sans supposer FastAPI.

    Args:
        health_url: Endpoint de santé complet configuré pour le service.
        client: Client externe injecté si nécessaire.

    Raises:
        RagApiError: Si le service n'est pas disponible.
    """
    logger.info(
        "checking api health", extra={"service": "rag_ihm", "event": "api_health_check"}
    )
    (client or create_rag_client()).check_health(health_url)


def ask_question(
    config: ChatApiConfig,
    question: str,
    provider: str,
    access_token: str | None,
    client: RagClient | None = None,
) -> AskQuestionResponse:
    """Orchestre l'envoi d'une question authentifiée à l'orchestrator.

    Args:
        config: Endpoints orchestrator.
        question: Question utilisateur, non loggée.
        provider: Provider LLM demandé.
        access_token: Bearer token de la session.
        client: Client externe injecté si nécessaire.

    Returns:
        DTO de réponse du chat.

    Raises:
        RagApiError: Si la session manque ou si la réponse est invalide.
    """
    payload = _authenticated_request(
        "POST",
        config.ask_question_url,
        access_token,
        payload={"question": question, "provider": provider, "channel": "streamlit"},
        timeout=360,
        client=client,
    )
    try:
        return validate_ask_question_response(payload)
    except ResponseContractError as exception:
        raise RagApiError(
            "Le service RAG a retourné une réponse invalide.",
            {"contract": "ask_question", "dependency": "rag_orchestrator"},
            code="response_contract_error",
        ) from exception


def get_authenticated_user(
    config: ChatApiConfig,
    access_token: str | None,
    client: RagClient | None = None,
) -> AuthenticatedUser:
    """Charge l'identité validée par l'orchestrator depuis `/auth/me`.

    Args:
        config: Endpoints permettant de calculer la base orchestrator.
        access_token: Bearer token reçu de Pocket ID.
        client: Client externe injecté si nécessaire.

    Returns:
        Profil dont le token et les claims ont été validés côté backend.

    Raises:
        RagApiError: Si le profil ne possède pas son identité stable minimale.
    """
    payload = _authenticated_request(
        "GET", _orchestrator_url(config, "/auth/me"), access_token, client=client
    )
    try:
        return validate_authenticated_user(payload)
    except ResponseContractError as exception:
        raise RagApiError(
            "Le profil utilisateur retourné est invalide.",
            {"contract": "authenticated_user", "dependency": "rag_orchestrator"},
            code="response_contract_error",
        ) from exception


def get_my_quota_usage(
    config: ChatApiConfig,
    access_token: str | None,
    client: RagClient | None = None,
) -> QuotaUsageResponse:
    """Récupère le quota de l'utilisateur connecté.

    Args:
        config: Endpoints orchestrator.
        access_token: Bearer token de la session.
        client: Client externe injecté si nécessaire.

    Returns:
        Données de quota validées comme objet JSON.
    """
    payload = _authenticated_request(
        "GET",
        _orchestrator_url(config, "/usage/quota/me"),
        access_token,
        client=client,
    )
    try:
        return validate_quota_usage_response(payload)
    except ResponseContractError as exception:
        raise _quota_contract_error(exception) from exception


def list_admin_quota_usages(
    config: ChatApiConfig,
    access_token: str | None,
    client: RagClient | None = None,
) -> list[QuotaUsageResponse]:
    """Liste les quotas visibles par un administrateur.

    Args:
        config: Endpoints orchestrator.
        access_token: Bearer token de la session.
        client: Client externe injecté si nécessaire.

    Returns:
        Liste validée d'objets quota.
    """
    payload = _authenticated_request(
        "GET",
        _orchestrator_url(config, "/usage/quota/admin/users"),
        access_token,
        client=client,
    )
    try:
        return validate_quota_usage_list(payload)
    except ResponseContractError as exception:
        raise _quota_contract_error(exception) from exception


def update_admin_quota_usage(
    config: ChatApiConfig,
    access_token: str | None,
    user_id: str,
    max_tokens_par_mois: int,
    actif: bool,
    illimite: bool,
    client: RagClient | None = None,
) -> QuotaUsageResponse:
    """Met à jour le quota d'un utilisateur via l'orchestrator.

    Args:
        config: Endpoints orchestrator.
        access_token: Bearer token de la session.
        user_id: Identifiant stable de l'utilisateur ciblé.
        max_tokens_par_mois: Nouveau plafond mensuel.
        actif: État d'activation du quota.
        illimite: Indique si le plafond mensuel doit être ignoré.
        client: Client externe injecté si nécessaire.

    Returns:
        Quota mis à jour validé comme objet JSON.
    """
    payload = _authenticated_request(
        "PATCH",
        _orchestrator_url(config, f"/usage/quota/admin/users/{user_id}"),
        access_token,
        payload={
            "max_tokens_par_mois": max_tokens_par_mois,
            "actif": actif,
            "illimite": illimite,
        },
        client=client,
    )
    try:
        return validate_quota_usage_response(payload)
    except ResponseContractError as exception:
        raise _quota_contract_error(exception) from exception


def list_admin_interaction_feedbacks(
    config: ChatApiConfig,
    access_token: str | None,
    start_date: date,
    end_date: date,
    client: RagClient | None = None,
) -> list[AdminInteractionFeedback]:
    """Liste les feedbacks administrateur sur une période.

    Args:
        config: Endpoints orchestrator.
        access_token: Bearer token de la session.
        start_date: Date de début incluse.
        end_date: Date de fin incluse.
        client: Client externe injecté si nécessaire.

    Returns:
        Liste validée d'objets feedback.
    """
    payload = _authenticated_request(
        "GET",
        _orchestrator_url(config, "/usage/admin/interactions/feedbacks"),
        access_token,
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        client=client,
    )
    try:
        return validate_admin_feedback_list(payload)
    except ResponseContractError as exception:
        raise RagApiError(
            "Le service RAG a retourné des avis invalides.",
            {"contract": "admin_feedbacks", "dependency": "rag_orchestrator"},
            code="response_contract_error",
        ) from exception


def submit_interaction_feedback(
    config: ChatApiConfig,
    access_token: str | None,
    interaction_id: int,
    note: int,
    commentaire: str | None,
    client: RagClient | None = None,
) -> FeedbackResponse:
    """Enregistre un feedback lié à une réponse RAG.

    Args:
        config: Endpoints orchestrator.
        access_token: Bearer token de la session.
        interaction_id: Interaction évaluée.
        note: Vote positif ou négatif.
        commentaire: Commentaire utilisateur facultatif.
        client: Client externe injecté si nécessaire.

    Returns:
        Feedback sauvegardé validé comme objet JSON.
    """
    payload = _authenticated_request(
        "POST",
        _orchestrator_url(config, f"/usage/interactions/{interaction_id}/feedback"),
        access_token,
        payload={"note": note, "commentaire": commentaire},
        client=client,
    )
    try:
        return validate_feedback_response(payload)
    except ResponseContractError as exception:
        raise RagApiError(
            "Le service RAG a retourné un avis invalide.",
            {"contract": "feedback", "dependency": "rag_orchestrator"},
            code="response_contract_error",
        ) from exception


def run_evaluation(
    config: EvaluatorApiConfig,
    access_token: str | None,
    client: RagClient | None = None,
    *,
    question_limit: int | None = None,
) -> EvaluationResponse:
    """Déclenche l'évaluation en propageant l'identité si le service l'accepte.

    Args:
        config: Endpoints evaluator.
        access_token: Bearer token transmis à l'evaluator.
        client: Client externe injecté si nécessaire.
        question_limit: Nombre de premières questions à évaluer.

    Returns:
        DTO des résultats d'évaluation.

    Raises:
        RagApiError: Si la session manque ou si le résultat est invalide.
    """
    payload = _authenticated_request(
        "POST",
        config.evaluate_url,
        access_token,
        timeout=300,
        payload=(
            {"question_limit": question_limit} if question_limit is not None else None
        ),
        client=client,
    )
    try:
        return validate_evaluation_response(payload)
    except ResponseContractError as exception:
        raise RagApiError(
            "Le service d'évaluation a retourné une réponse invalide.",
            {"contract": "evaluation", "dependency": "rag_evaluator"},
            code="response_contract_error",
        ) from exception


def _required_env(name: str) -> str:
    """Lit une variable d'environnement obligatoire.

    Args:
        name: Nom de la variable.

    Returns:
        Valeur non vide.

    Raises:
        RagApiError: Si la variable est absente.
    """
    value = os.getenv(name)
    if not value:
        raise RagApiError(
            "La configuration de l'interface est incomplète.",
            {"configuration": name},
            code="configuration_error",
        )
    return value


def _orchestrator_url(config: ChatApiConfig, path: str) -> str:
    """Joint un chemin absolu à la base orchestrator normalisée.

    Args:
        config: Configuration contenant l'endpoint de question.
        path: Chemin d'API commençant par `/`.

    Returns:
        URL complète sans double slash de chemin.
    """
    return f"{config.base_url}/{path.lstrip('/')}"


def _usage_url(config: ChatApiConfig, path: str) -> str:
    """Conserve le helper historique en utilisant la base robuste.

    Args:
        config: Configuration contenant l'endpoint de question.
        path: Chemin usage à joindre.

    Returns:
        URL complète de l'endpoint usage.
    """
    return _orchestrator_url(config, path)


def _authenticated_request(
    method: str,
    url: str,
    access_token: str | None,
    *,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
    client: RagClient | None = None,
) -> JsonValue:
    """Exécute un appel RAG authentifié via le client DAL.

    Args:
        method: Méthode HTTP cible.
        url: Endpoint complet.
        access_token: Bearer token obligatoire.
        params: Paramètres de query string.
        payload: Corps JSON.
        timeout: Durée maximale de l'appel.
        client: Client externe injecté si nécessaire.

    Returns:
        Corps JSON décodé.

    Raises:
        RagApiError: Si la session est absente.
    """
    if not access_token:
        raise RagApiError(
            "La session a expiré. Reconnecte-toi pour continuer.",
            {"status_code": 401},
            code="authentication_required",
        )
    return (client or create_rag_client()).request_json(
        method,
        url,
        timeout=timeout,
        access_token=access_token,
        params=params,
        payload=payload,
    )


def _expect_dict(payload: JsonValue) -> dict[str, Any]:
    """Valide qu'un corps JSON est un objet.

    Args:
        payload: Corps JSON à contrôler.

    Returns:
        Objet JSON typé pour la frontière de service.

    Raises:
        RagApiError: Si le type racine est inattendu.
    """
    if not isinstance(payload, dict):
        raise RagApiError(
            "Le service a retourné un format inattendu.",
            {"contract": "json_object"},
            code="response_contract_error",
        )
    return cast(dict[str, Any], payload)


def _expect_dict_list(payload: JsonValue) -> list[dict[str, Any]]:
    """Valide qu'un corps JSON est une liste d'objets.

    Args:
        payload: Corps JSON à contrôler.

    Returns:
        Liste d'objets JSON.

    Raises:
        RagApiError: Si la liste contient une valeur incompatible.
    """
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise RagApiError(
            "Le service a retourné un format inattendu.",
            {"contract": "json_object_list"},
            code="response_contract_error",
        )
    return cast(list[dict[str, Any]], payload)


def _auth_headers(access_token: str) -> dict[str, str]:
    """Construit l'en-tête bearer pour les tests et intégrations existants.

    Args:
        access_token: Token à transmettre.

    Returns:
        En-tête Authorization.
    """
    return {"Authorization": f"Bearer {access_token}"}


def _docs_url(health_url: str) -> str:
    """Retourne sans modification l'URL explicite de healthcheck.

    Args:
        health_url: Endpoint de santé configuré.

    Returns:
        Même URL, normalisée uniquement des espaces extérieurs.
    """
    return health_url.strip()


def _extract_error_message(details: dict[str, Any]) -> str:
    """Retourne un message stable sans recopier les détails backend.

    Args:
        details: Métadonnées techniques sûres ignorées pour l'affichage.

    Returns:
        Message utilisateur générique.
    """
    return "Le service RAG a retourné une erreur."


def _truncate(value: str, limit: int = 1000) -> str:
    """Tronque une chaîne non affichée afin de préserver l'ancien helper.

    Args:
        value: Chaîne à borner.
        limit: Nombre maximal de caractères.

    Returns:
        Valeur éventuellement tronquée.
    """
    if len(value) <= limit:
        return value
    return f"{value[:limit].rstrip()}..."


def _quota_contract_error(exception: ResponseContractError) -> RagApiError:
    """Traduit une erreur de contrat quota sans reprendre sa valeur brute.

    Args:
        exception: Erreur de validation utilisée uniquement comme cause chaînée.

    Returns:
        Erreur publique stable pour le point central Streamlit.
    """
    return RagApiError(
        "Le service RAG a retourné un quota invalide.",
        {"contract": "quota_usage", "dependency": "rag_orchestrator"},
        code="response_contract_error",
    )
