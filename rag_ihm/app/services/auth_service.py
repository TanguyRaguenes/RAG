import base64
import hashlib
import hmac
import html
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Never
from urllib.parse import urlencode

import streamlit as st

from app.core.errors import RagApiError
from app.dal.clients.http_client import RequestsHttpClient
from app.dal.clients.oidc_client import OidcClient
from app.schemas.api import AuthenticatedUser, TokenResponse
from app.services.rag_api_client import get_authenticated_user, load_chat_api_config

ACCESS_TOKEN_KEY = "auth_access_token"
USER_KEY = "auth_user"
IDENTITY_VERIFIED_KEY = "auth_identity_verified"
OAUTH_STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class OidcConfig:
    """Configuration OIDC utilisée par l'IHM Streamlit."""

    authorize_url: str
    token_url: str
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str
    scope: str


def _get_required_env(name: str) -> str:
    """Lit une variable d'environnement OIDC obligatoire.

    Args:
        name: Nom de la variable à lire.

    Returns:
        Valeur non vide de la variable.

    Raises:
        RagApiError: Si la variable est absente de la configuration.
    """
    value = os.getenv(name)
    if not value:
        raise RagApiError(
            "La configuration de l'authentification est incomplète.",
            {"configuration": name},
            code="configuration_error",
        )

    return value


def get_oidc_config() -> OidcConfig:
    """Charge la configuration OIDC depuis l'environnement.

    Returns:
        Configuration OIDC validée.
    """
    return OidcConfig(
        authorize_url=_get_required_env("RAG_IHM_OIDC_AUTHORIZE_URL"),
        token_url=_get_required_env("RAG_IHM_OIDC_TOKEN_URL"),
        client_id=_get_required_env("RAG_IHM_OIDC_CLIENT_ID"),
        client_secret=_get_required_env("RAG_IHM_OIDC_CLIENT_SECRET"),
        redirect_uri=_get_required_env("RAG_IHM_OIDC_REDIRECT_URI"),
        scope=os.getenv("RAG_IHM_OIDC_SCOPE", "openid email profile groups"),
    )


def is_authenticated() -> bool:
    """Indique si le token et le profil backend vérifié sont présents.

    Returns:
        `True` si l'utilisateur est considéré authentifié.
    """
    return bool(
        st.session_state.get(ACCESS_TOKEN_KEY)
        and st.session_state.get(USER_KEY)
        and st.session_state.get(IDENTITY_VERIFIED_KEY) is True
    )


def get_access_token() -> str | None:
    """Retourne l'access token courant.

    Returns:
        Token OIDC stocké en session ou `None`.
    """
    return st.session_state.get(ACCESS_TOKEN_KEY)


def get_current_user() -> AuthenticatedUser | None:
    """Retourne les claims utilisateur courants.

    Returns:
        Claims utilisateur fusionnés ou `None` si absent.
    """
    user = st.session_state.get(USER_KEY)
    return user if isinstance(user, dict) else None


def is_usage_admin(current_user: AuthenticatedUser | None) -> bool:
    """Détermine si l'utilisateur possède un groupe admin usage.

    Args:
        current_user: Claims utilisateur courants.

    Returns:
        `True` si l'utilisateur appartient à un groupe admin configuré.
    """
    return _is_admin_for_groups(current_user, "RAG_USAGE_ADMIN_GROUPS")


def is_evaluator_admin(current_user: AuthenticatedUser | None) -> bool:
    """Détermine si l'utilisateur peut lancer les évaluations RAG.

    Args:
        current_user: Claims utilisateur courants.

    Returns:
        `True` si l'utilisateur appartient à un groupe evaluator configuré.
    """
    return _is_admin_for_groups(current_user, "RAG_EVALUATOR_ADMIN_GROUPS")


def logout() -> None:
    """Supprime toutes les données utilisateur de la session et de l'URL."""
    st.session_state.clear()
    st.query_params.clear()


def build_login_url() -> str:
    """Construit l'URL d'autorisation OIDC.

    Returns:
        URL de login avec paramètres OAuth et state.
    """
    config = get_oidc_config()
    state_binding = _oauth_state_binding(config)
    state = _build_oauth_state(config.client_secret, state_binding)
    params = build_authorization_params(config, state)

    return f"{config.authorize_url}?{urlencode(params)}"


def _build_oauth_state(client_secret: str, binding: str = "") -> str:
    """Crée un state signé, stateless et lié à la configuration OAuth.

    Args:
        client_secret: Clé HMAC connue uniquement de l'IHM et de Pocket ID.
        binding: Empreinte du client et de l'URI de retour.

    Returns:
        State vérifiable pendant dix minutes sans dépendre de `session_state`.
    """
    payload = f"{int(time.time())}.{secrets.token_urlsafe(32)}"
    signature = hmac.new(
        client_secret.encode(), f"{payload}.{binding}".encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def _is_valid_oauth_state(
    state: str | None,
    client_secret: str,
    binding: str = "",
) -> bool:
    """Vérifie la signature, la liaison OAuth et l'âge maximal du state.

    Args:
        state: State retourné par Pocket ID.
        client_secret: Clé HMAC de l'IHM.
        binding: Empreinte attendue du client et de l'URI de retour.

    Returns:
        `True` uniquement pour un state authentique âgé d'au plus dix minutes.
    """
    if not state:
        return False

    try:
        issued_at_text, nonce, signature = state.split(".", 2)
        issued_at = int(issued_at_text)
    except (TypeError, ValueError):
        return False

    age = int(time.time()) - issued_at
    if not nonce or age < 0 or age > OAUTH_STATE_TTL_SECONDS:
        return False

    payload = f"{issued_at_text}.{nonce}"
    bound_payload = f"{payload}.{binding}"
    expected_signature = (
        base64.urlsafe_b64encode(
            hmac.new(
                client_secret.encode(), bound_payload.encode(), hashlib.sha256
            ).digest()
        )
        .decode()
        .rstrip("=")
    )
    return hmac.compare_digest(signature, expected_signature)


def _oauth_state_binding(config: OidcConfig) -> str:
    """Lie le state au client OIDC et à son URI de retour.

    Args:
        config: Configuration OAuth active au début ou à la fin du flux.

    Returns:
        Empreinte stable ne révélant pas le secret du client.
    """
    value = f"{config.client_id}\0{config.redirect_uri}"
    return hashlib.sha256(value.encode()).hexdigest()


def build_authorization_params(config: OidcConfig, state: str) -> dict[str, str]:
    """Construit les paramètres OAuth d'autorisation.

    Args:
        config: Configuration OIDC.
        state: Jeton CSRF OAuth généré côté session.

    Returns:
        Paramètres de requête OAuth.
    """
    return {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scope,
        "state": state,
    }


def _query_param_value(name: str) -> str | None:
    """Récupère une valeur de query parameter Streamlit de manière compatible liste ou scalaire.

    Args:
        name: Nom de variable, champ ou ressource à lire.

    Returns:
        Première valeur du query parameter, ou `None` s'il est absent.
    """
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None

    return value


def _exchange_code_for_tokens(code: str) -> TokenResponse:
    """Échange le code OAuth reçu contre les tokens OIDC.

    Args:
        code: Code OAuth retourné par le fournisseur d'identité.

    Returns:
        Réponse token OIDC retournée par le fournisseur d'identité.
    """
    config = get_oidc_config()
    return OidcClient(RequestsHttpClient()).exchange_code(
        token_url=config.token_url,
        client_id=config.client_id,
        client_secret=config.client_secret,
        code=code,
        redirect_uri=config.redirect_uri,
    )


def handle_oidc_callback() -> None:
    """Traite le retour OIDC après authentification et alimente la session Streamlit."""
    error = _query_param_value("error")
    if error:
        _stop_oidc_callback(
            RagApiError(
                "Authentification refusée par Pocket ID.",
                code="oidc_authorization_denied",
            )
        )

    code = _query_param_value("code")
    if not code:
        return

    try:
        config = get_oidc_config()
    except RagApiError as auth_error:
        _stop_oidc_callback(auth_error)
    returned_state = _query_param_value("state")
    if not _is_valid_oauth_state(
        returned_state,
        config.client_secret,
        _oauth_state_binding(config),
    ):
        _stop_oidc_callback(
            RagApiError(
                "État OAuth invalide. Recommence la connexion.",
                code="oidc_state_invalid",
            ),
            clear_session=True,
        )

    try:
        token_response = _exchange_code_for_tokens(code)
    except RagApiError as auth_error:
        _stop_oidc_callback(
            RagApiError(
                "Pocket ID a refusé la connexion. Recommence l'authentification.",
                auth_error.safe_details,
                code="oidc_token_exchange_error",
                retryable=auth_error.retryable,
            )
        )

    access_token = token_response.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        _stop_oidc_callback(
            RagApiError(
                "Pocket ID a retourné une réponse inattendue.",
                {"contract": "oidc_token", "dependency": "pocket_id"},
                code="oidc_response_contract_error",
            )
        )

    try:
        verified_user = get_authenticated_user(load_chat_api_config(), access_token)
    except RagApiError as auth_error:
        _stop_oidc_callback(
            RagApiError(
                "L'identité Pocket ID n'a pas pu être vérifiée par le service RAG.",
                auth_error.safe_details,
                code="oidc_identity_verification_error",
                retryable=auth_error.retryable,
            ),
            clear_session=True,
        )

    st.session_state[ACCESS_TOKEN_KEY] = access_token
    st.session_state[USER_KEY] = verified_user
    st.session_state[IDENTITY_VERIFIED_KEY] = True

    st.query_params.clear()
    st.rerun()


def _stop_oidc_callback(
    error: RagApiError,
    *,
    clear_session: bool = False,
) -> Never:
    """Nettoie un callback OAuth échoué avant d'interrompre Streamlit.

    Args:
        error: Erreur publique transmise au point central Streamlit.
        clear_session: Indique si les données de session doivent aussi être supprimées.
    """
    if clear_session:
        st.session_state.clear()

    for parameter in ("code", "state", "error"):
        if parameter in st.query_params:
            del st.query_params[parameter]

    from app.components.common import render_api_error

    render_api_error(error)
    st.stop()


def require_authenticated_user() -> AuthenticatedUser | None:
    """Exige un utilisateur authentifié ou affiche le bouton de connexion.

    Returns:
        Claims de l'utilisateur connecté après vérification de session.
    """
    if is_authenticated():
        return get_current_user()

    try:
        login_url = html.escape(build_login_url(), quote=True)
    except RagApiError as error:
        _stop_oidc_callback(error)
    st.title("IsiDore")
    st.caption("Assistant RAG sur la documentation interne ISILOG.")
    st.html(f'<a href="{login_url}" target="_self">Se connecter</a>')
    st.stop()


def _normalize_groups(groups: object) -> set[str]:
    """Normalise une liste de groupes pour permettre des comparaisons insensibles à la casse.

    Args:
        groups: Groupes ou rôles OIDC à normaliser avant contrôle d'autorisation.

    Returns:
        Valeur normalisée prête à être comparée, stockée ou affichée.
    """
    if isinstance(groups, dict):
        groups = [groups]

    normalized_groups: set[str] = set()

    if not isinstance(groups, list | tuple | set):
        groups = [groups]

    for group in groups:
        if isinstance(group, dict):
            value = group.get("name") or group.get("display_name") or group.get("id")
        else:
            value = group

        if value is None:
            continue

        normalized_group = str(value).strip().lower()

        if normalized_group:
            normalized_groups.add(normalized_group)

    return normalized_groups


def _is_admin_for_groups(
    current_user: AuthenticatedUser | None,
    environment_name: str,
) -> bool:
    """Compare les groupes utilisateur aux groupes d'un périmètre administratif.

    Args:
        current_user: Claims utilisateur vérifiés par l'orchestrator.
        environment_name: Variable CSV partagée avec le service protégé.

    Returns:
        `True` si au moins un groupe utilisateur autorise le périmètre.
    """
    if not current_user:
        return False

    admin_groups = _normalize_groups(
        os.getenv(environment_name, "rag_admin").split(",")
    )
    return bool(_normalize_groups(_extract_user_groups(current_user)) & admin_groups)


def _extract_user_groups(current_user: AuthenticatedUser) -> list[Any]:
    """Extrait les groupes ou rôles depuis les claims utilisateur.

    Args:
        current_user: Utilisateur authentifié issu du token OIDC courant.

    Returns:
        Liste des groupes ou rôles extraits des claims utilisateur.
    """
    user_groups = (
        current_user.get("groups")
        or current_user.get("roles")
        or current_user.get("role")
        or []
    )

    if isinstance(user_groups, str):
        return [user_groups]

    if isinstance(user_groups, list):
        return user_groups

    return [user_groups]
