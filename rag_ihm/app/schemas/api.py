import math
from typing import Any, NotRequired, TypedDict, cast

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class AuthenticatedUser(TypedDict):
    """Profil utilisateur validé et retourné par l'orchestrator."""

    issuer: str
    sub: str
    email: NotRequired[str | None]
    name: NotRequired[str | None]
    display_name: NotRequired[str | None]
    preferred_username: NotRequired[str | None]
    groups: NotRequired[list[str]]


class TokenResponse(TypedDict, total=False):
    """Réponse utile de l'endpoint token Pocket ID."""

    access_token: str
    id_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class QuotaUsageResponse(TypedDict):
    """Quota mensuel retourné par l'orchestrator."""

    utilisateur_id: str
    email: str | None
    display_name: str | None
    preferred_username: str | None
    max_tokens_par_mois: int
    consumed_tokens: int
    remaining_tokens: int
    usage_ratio: float
    actif: bool
    date_debut: str
    date_fin: str | None


class FeedbackResponse(TypedDict):
    """Confirmation d'un avis enregistré pour une interaction."""

    interaction_id: int
    note: int
    commentaire: str | None


class AdminInteractionFeedback(TypedDict):
    """Avis détaillé visible dans l'écran d'administration."""

    interaction_id: int
    cree_le: str
    question: str
    reponse: str | None
    note: int | None
    commentaire: str | None
    chunks: list[dict[str, Any]]


class AskQuestionResponse(TypedDict):
    """Réponse complète de l'orchestrator, hors identifiant optionnel."""

    interaction_id: NotRequired[int | None]
    llm_response: str
    retrieved_documents: dict[str, int]
    retrieved_chunks: list[dict[str, Any]]
    model: str
    duration: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    generated_prompt: list[dict[str, Any]]


class ChatMessage(TypedDict, total=False):
    """Message conservé dans la session Streamlit."""

    role: str
    content: str
    interaction_id: int
    retrieved_documents: dict[str, int]
    retrieved_chunks: list[dict[str, Any]]
    model: str
    duration: str
    total_tokens: int
    generated_prompt: list[dict[str, Any]]
    feedback: dict[str, Any]


class RetrievalEvaluation(TypedDict):
    """Métriques documentaires obligatoires retournées par l'evaluator."""

    mrr: float
    ndcg: float
    recall: float
    precision: float
    source_hit_at_5: float


class AnswerEvaluation(TypedDict):
    """Métriques de réponse obligatoires retournées par l'evaluator."""

    feedback: str
    accuracy: float
    completeness: float
    relevance: float
    faithfulness: float
    safe_refusal: float


class EvaluationResponse(TypedDict):
    """Agrégats complets retournés par l'evaluator."""

    average_retrieval: RetrievalEvaluation
    average_answer_quality: AnswerEvaluation
    total_duration: str
    total_questions: int


class ResponseContractError(ValueError):
    """Signale une réponse interservice incompatible avec le contrat IHM."""


def validate_token_response(payload: object) -> TokenResponse:
    """Valide la réponse OIDC avant tout stockage en session.

    Args:
        payload: Corps JSON décodé retourné par l'endpoint token.

    Returns:
        Réponse token dont les champs présents possèdent les types attendus.

    Raises:
        ResponseContractError: Si l'access token manque ou si un champ est invalide.
    """
    data = _require_dict(payload, "oidc_token")
    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise ResponseContractError("oidc_token.access_token est absent ou invalide")

    for field in ("id_token", "refresh_token", "token_type"):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ResponseContractError(f"oidc_token.{field} est invalide")

    expires_in = data.get("expires_in")
    if expires_in is not None and (not _is_integer(expires_in) or expires_in < 0):
        raise ResponseContractError("oidc_token.expires_in est invalide")
    return cast(TokenResponse, data)


def validate_authenticated_user(payload: object) -> AuthenticatedUser:
    """Valide l'identité minimale confirmée par l'orchestrator.

    Args:
        payload: Profil JSON retourné par `/auth/me`.

    Returns:
        Identité stable et groupes correctement typés.

    Raises:
        ResponseContractError: Si les claims stables ou les groupes sont invalides.
    """
    data = _require_dict(payload, "authenticated_user")
    _require_non_empty_string_fields(data, "issuer", "sub")
    groups = data.get("groups", [])
    if not isinstance(groups, list) or not all(
        isinstance(group, str) for group in groups
    ):
        raise ResponseContractError("authenticated_user.groups est invalide")
    for field in ("email", "name", "display_name", "preferred_username"):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ResponseContractError(f"authenticated_user.{field} est invalide")
    return cast(AuthenticatedUser, data)


def validate_quota_usage_response(payload: object) -> QuotaUsageResponse:
    """Valide un quota avant son utilisation par les composants Streamlit.

    Args:
        payload: Objet quota retourné par l'orchestrator.

    Returns:
        Quota complet avec nombres finis et champs d'affichage sûrs.

    Raises:
        ResponseContractError: Si un champ obligatoire manque ou est mal typé.
    """
    data = _require_dict(payload, "quota_usage")
    _require_non_empty_string_fields(data, "utilisateur_id", "date_debut")
    _require_integer_fields(
        data,
        "max_tokens_par_mois",
        "consumed_tokens",
        "remaining_tokens",
    )
    if not _is_number(data.get("usage_ratio")):
        raise ResponseContractError("quota_usage.usage_ratio est invalide")
    if not isinstance(data.get("actif"), bool):
        raise ResponseContractError("quota_usage.actif est invalide")
    for field in ("email", "display_name", "preferred_username", "date_fin"):
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            raise ResponseContractError(f"quota_usage.{field} est invalide")
    return cast(QuotaUsageResponse, data)


def validate_quota_usage_list(payload: object) -> list[QuotaUsageResponse]:
    """Valide chaque quota de la liste administrateur.

    Args:
        payload: Liste JSON retournée par l'endpoint administrateur.

    Returns:
        Liste de quotas complets.

    Raises:
        ResponseContractError: Si la racine ou un élément est invalide.
    """
    if not isinstance(payload, list):
        raise ResponseContractError("quota_usage_list doit être une liste")
    return [validate_quota_usage_response(item) for item in payload]


def validate_feedback_response(payload: object) -> FeedbackResponse:
    """Valide la confirmation retournée après soumission d'un avis.

    Args:
        payload: Objet JSON de confirmation du feedback.

    Returns:
        Confirmation contenant l'interaction, la note et le commentaire optionnel.

    Raises:
        ResponseContractError: Si la confirmation est malformée.
    """
    data = _require_dict(payload, "feedback")
    _require_integer_fields(data, "interaction_id", "note")
    if data["note"] not in (-1, 1):
        raise ResponseContractError("feedback.note est invalide")
    commentaire = data.get("commentaire")
    if commentaire is not None and not isinstance(commentaire, str):
        raise ResponseContractError("feedback.commentaire est invalide")
    return cast(FeedbackResponse, data)


def validate_admin_feedback_list(
    payload: object,
) -> list[AdminInteractionFeedback]:
    """Valide les feedbacks et chunks affichés dans l'écran administrateur.

    Args:
        payload: Liste JSON retournée pour une période d'administration.

    Returns:
        Liste de feedbacks dont tous les champs affichés sont contrôlés.

    Raises:
        ResponseContractError: Si une interaction ou un chunk est malformé.
    """
    if not isinstance(payload, list):
        raise ResponseContractError("admin_feedbacks doit être une liste")

    validated: list[AdminInteractionFeedback] = []
    for item in payload:
        data = _require_dict(item, "admin_feedback")
        _require_integer_fields(data, "interaction_id")
        _require_string_fields(data, "cree_le", "question")
        for field in ("reponse", "commentaire"):
            value = data.get(field)
            if value is not None and not isinstance(value, str):
                raise ResponseContractError(f"admin_feedback.{field} est invalide")
        note = data.get("note")
        if note is not None and (not _is_integer(note) or note not in (-1, 1)):
            raise ResponseContractError("admin_feedback.note est invalide")
        chunks = data.get("chunks")
        if not isinstance(chunks, list):
            raise ResponseContractError("admin_feedback.chunks est invalide")
        for chunk in chunks:
            _validate_admin_feedback_chunk(chunk)
        validated.append(cast(AdminInteractionFeedback, data))
    return validated


def validate_ask_question_response(payload: object) -> AskQuestionResponse:
    """Valide strictement tous les champs de réponse du chat.

    Args:
        payload: Corps JSON décodé reçu de l'orchestrator.

    Returns:
        Même dictionnaire, désormais conforme au contrat du chat.

    Raises:
        ResponseContractError: Si un champ obligatoire manque ou possède un type invalide.
    """
    data = _require_dict(payload, "ask_question")
    _require_string_fields(data, "llm_response", "model", "duration")
    _require_integer_fields(data, "input_tokens", "output_tokens", "total_tokens")

    interaction_id = data.get("interaction_id")
    if (
        "interaction_id" in data
        and interaction_id is not None
        and not _is_integer(interaction_id)
    ):
        raise ResponseContractError("ask_question.interaction_id est invalide")

    retrieved_documents = _require_dict_field(data, "retrieved_documents")
    if not all(
        isinstance(document, str) and _is_integer(count)
        for document, count in retrieved_documents.items()
    ):
        raise ResponseContractError("ask_question.retrieved_documents est invalide")

    _require_dict_list_field(data, "retrieved_chunks")
    _require_dict_list_field(data, "generated_prompt")

    return cast(AskQuestionResponse, data)


def validate_evaluation_response(payload: object) -> EvaluationResponse:
    """Valide strictement la réponse complète du service evaluator.

    Args:
        payload: Corps JSON décodé reçu de l'evaluator.

    Returns:
        Même dictionnaire, désormais conforme au contrat du dashboard.

    Raises:
        ResponseContractError: Si un agrégat ou une métrique est absent ou invalide.
    """
    data = _require_dict(payload, "evaluation")
    _require_string_fields(data, "total_duration")
    _require_integer_fields(data, "total_questions")

    retrieval = _require_dict_field(data, "average_retrieval")
    _require_number_fields(
        retrieval,
        "mrr",
        "ndcg",
        "recall",
        "precision",
        "source_hit_at_5",
    )

    answer = _require_dict_field(data, "average_answer_quality")
    _require_string_fields(answer, "feedback")
    _require_number_fields(
        answer,
        "accuracy",
        "completeness",
        "relevance",
        "faithfulness",
        "safe_refusal",
    )

    return cast(EvaluationResponse, data)


def _require_dict(payload: object, contract: str) -> dict[str, Any]:
    """Exige un objet dictionnaire à la racine d'un contrat JSON.

    Args:
        payload: Valeur à contrôler.
        contract: Nom sûr du contrat utilisé dans le diagnostic.

    Returns:
        Objet JSON validé.

    Raises:
        ResponseContractError: Si la valeur n'est pas un dictionnaire.
    """
    if not isinstance(payload, dict):
        raise ResponseContractError(f"{contract} doit être un objet")
    return cast(dict[str, Any], payload)


def _require_dict_field(data: dict[str, Any], field: str) -> dict[str, Any]:
    """Exige un champ objet dans une réponse JSON.

    Args:
        data: Objet JSON parent.
        field: Champ obligatoire à contrôler.

    Returns:
        Dictionnaire contenu dans le champ.

    Raises:
        ResponseContractError: Si le champ est absent ou n'est pas un objet.
    """
    value = data.get(field)
    if not isinstance(value, dict):
        raise ResponseContractError(f"{field} est absent ou invalide")
    return cast(dict[str, Any], value)


def _require_dict_list_field(data: dict[str, Any], field: str) -> None:
    """Exige un champ contenant uniquement une liste d'objets JSON.

    Args:
        data: Objet JSON parent.
        field: Champ obligatoire à contrôler.

    Raises:
        ResponseContractError: Si le champ n'est pas une liste de dictionnaires.
    """
    value = data.get(field)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ResponseContractError(f"{field} est absent ou invalide")


def _require_string_fields(data: dict[str, Any], *fields: str) -> None:
    """Exige plusieurs champs chaîne sans conversion implicite.

    Args:
        data: Objet JSON à contrôler.
        fields: Noms des champs chaîne obligatoires.

    Raises:
        ResponseContractError: Si au moins un champ n'est pas une chaîne.
    """
    for field in fields:
        if not isinstance(data.get(field), str):
            raise ResponseContractError(f"{field} est absent ou invalide")


def _require_non_empty_string_fields(data: dict[str, Any], *fields: str) -> None:
    """Exige des champs chaîne obligatoires et non vides.

    Args:
        data: Objet JSON à contrôler.
        fields: Champs dont une valeur non vide est requise.

    Raises:
        ResponseContractError: Si un champ manque, est vide ou possède un autre type.
    """
    for field in fields:
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise ResponseContractError(f"{field} est absent ou invalide")


def _require_integer_fields(data: dict[str, Any], *fields: str) -> None:
    """Exige plusieurs champs entiers sans accepter les booléens.

    Args:
        data: Objet JSON à contrôler.
        fields: Noms des champs entiers obligatoires.

    Raises:
        ResponseContractError: Si au moins un champ n'est pas un entier strict.
    """
    for field in fields:
        if not _is_integer(data.get(field)):
            raise ResponseContractError(f"{field} est absent ou invalide")


def _require_number_fields(data: dict[str, Any], *fields: str) -> None:
    """Exige plusieurs nombres JSON finis sans accepter les booléens.

    Args:
        data: Objet JSON à contrôler.
        fields: Noms des champs numériques obligatoires.

    Raises:
        ResponseContractError: Si au moins un champ n'est pas un nombre fini.
    """
    for field in fields:
        if not _is_number(data.get(field)):
            raise ResponseContractError(f"{field} est absent ou invalide")


def _is_integer(value: object) -> bool:
    """Indique si une valeur est un entier JSON et non un booléen."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    """Indique si une valeur est un nombre JSON fini et non un booléen."""
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _validate_admin_feedback_chunk(payload: object) -> None:
    """Valide un chunk d'administration sans journaliser son contenu.

    Args:
        payload: Chunk JSON associé à une interaction.

    Raises:
        ResponseContractError: Si une métadonnée affichée possède un type invalide.
    """
    data = _require_dict(payload, "admin_feedback_chunk")
    _require_integer_fields(data, "rang")
    _require_string_fields(data, "titre", "chemin", "contenu")
    score = data.get("score")
    if score is not None and not _is_number(score):
        raise ResponseContractError("admin_feedback_chunk.score est invalide")
