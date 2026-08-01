import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st

ACCESS_TOKEN_KEY = "auth_access_token"
USER_KEY = "auth_user"
OAUTH_STATE_TTL_SECONDS = 600

AUTH_SESSION_KEYS = (
    ACCESS_TOKEN_KEY,
    USER_KEY,
)


@dataclass(frozen=True)
class OidcConfig:
    """Configuration OIDC utilisée par l'IHM Streamlit."""

    authorize_url: str
    token_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str


def _get_required_env(name: str) -> str:
    """Lit une variable d'environnement OIDC obligatoire.

    Args:
        name: Nom de la variable à lire.

    Returns:
        Valeur de la variable.
    """
    value = os.getenv(name)
    if not value:
        st.error(f"Variable d'environnement manquante : {name}")
        st.stop()

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
    """Indique si un access token est présent en session Streamlit.

    Returns:
        `True` si l'utilisateur est considéré authentifié.
    """
    return bool(st.session_state.get(ACCESS_TOKEN_KEY))


def get_access_token() -> str | None:
    """Retourne l'access token courant.

    Returns:
        Token OIDC stocké en session ou `None`.
    """
    return st.session_state.get(ACCESS_TOKEN_KEY)


def get_current_user() -> dict[str, Any] | None:
    """Retourne les claims utilisateur courants.

    Returns:
        Claims utilisateur fusionnés ou `None` si absent.
    """
    return st.session_state.get(USER_KEY)


def is_usage_admin(current_user: dict[str, Any] | None) -> bool:
    """Détermine si l'utilisateur possède un groupe admin usage.

    Args:
        current_user: Claims utilisateur courants.

    Returns:
        `True` si l'utilisateur appartient à un groupe admin configuré.
    """
    if not current_user:
        return False

    admin_groups = _normalize_groups(
        os.getenv("RAG_IHM_ADMIN_GROUPS", "rag_admin").split(",")
    )

    return bool(_normalize_groups(_extract_user_groups(current_user)) & admin_groups)


def logout() -> None:
    """Nettoie les clés d'authentification de la session Streamlit.

    Returns:
        Aucune valeur.
    """
    for key in AUTH_SESSION_KEYS:
        st.session_state.pop(key, None)


def build_login_url() -> str:
    """Construit l'URL d'autorisation OIDC.

    Returns:
        URL de login avec paramètres OAuth et state.
    """
    config = get_oidc_config()
    state = _build_oauth_state(config.client_secret)
    params = build_authorization_params(config, state)

    return f"{config.authorize_url}?{urlencode(params)}"


def _build_oauth_state(client_secret: str) -> str:
    """Crée un state OAuth signé qui reste vérifiable après le rechargement Streamlit."""
    payload = f"{int(time.time())}.{secrets.token_urlsafe(32)}"
    signature = hmac.new(
        client_secret.encode(), payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{payload}.{encoded_signature}"


def _is_valid_oauth_state(state: str | None, client_secret: str) -> bool:
    """Vérifie la signature et l'âge maximal du state OAuth reçu."""
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
    expected_signature = (
        base64.urlsafe_b64encode(
            hmac.new(client_secret.encode(), payload.encode(), hashlib.sha256).digest()
        )
        .decode()
        .rstrip("=")
    )
    return hmac.compare_digest(signature, expected_signature)


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


def _decode_jwt_payload_without_verification(token: str) -> dict[str, Any]:
    """Décode les claims d'un JWT sans vérifier la signature pour alimenter l'affichage utilisateur.

    Args:
        token: Token OIDC ou JWT à valider sans l'écrire dans les logs.

    Returns:
        Claims JSON décodés du token, ou dictionnaire vide en cas d'échec.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded_payload = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(decoded_payload)
    except (IndexError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
        return {}


def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Échange le code OAuth reçu contre les tokens OIDC.

    Args:
        code: Code OAuth retourné par le fournisseur d'identité.

    Returns:
        Réponse token OIDC retournée par le fournisseur d'identité.
    """
    config = get_oidc_config()
    response = requests.post(
        config.token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": config.redirect_uri,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


def handle_oidc_callback() -> None:
    """Traite le retour OIDC après authentification et alimente la session Streamlit."""
    error = _query_param_value("error")
    if error:
        st.error(f"Authentification refusée par Pocket ID : {error}")
        st.stop()

    code = _query_param_value("code")
    if not code:
        return

    returned_state = _query_param_value("state")
    if not _is_valid_oauth_state(returned_state, get_oidc_config().client_secret):
        logout()
        st.error("État OAuth invalide. Recommence la connexion.")
        st.stop()

    try:
        token_response = _exchange_code_for_tokens(code)
    except requests.HTTPError:
        st.error("Pocket ID a refusé la connexion. Recommence l'authentification.")
        st.stop()
    except requests.RequestException:
        st.error("Pocket ID est momentanément injoignable.")
        st.stop()

    access_token = token_response.get("access_token")
    if not access_token:
        st.error("Pocket ID n'a pas retourné d'access_token.")
        st.stop()

    st.session_state[ACCESS_TOKEN_KEY] = access_token
    id_claims = _decode_jwt_payload_without_verification(
        token_response.get("id_token", "")
    )
    access_claims = _decode_jwt_payload_without_verification(access_token)
    st.session_state[USER_KEY] = _merge_user_claims(id_claims, access_claims)

    st.query_params.clear()
    st.rerun()


def require_authenticated_user() -> dict[str, Any] | None:
    """Exige un utilisateur authentifié ou affiche le bouton de connexion.

    Returns:
        Claims de l'utilisateur connecté après vérification de session.
    """
    if is_authenticated():
        return get_current_user()

    st.title("IsiDore")
    st.caption("Assistant RAG sur la documentation interne ISILOG.")
    st.link_button("Se connecter", build_login_url(), type="primary")
    st.stop()


def _normalize_groups(groups) -> set[str]:
    """Normalise une liste de groupes pour permettre des comparaisons insensibles à la casse.

    Args:
        groups: Groupes ou rôles OIDC à normaliser avant contrôle d'autorisation.

    Returns:
        Valeur normalisée prête à être comparée, stockée ou affichée.
    """
    if isinstance(groups, dict):
        groups = [groups]

    normalized_groups: set[str] = set()

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


def _extract_user_groups(current_user: dict[str, Any]) -> list[Any]:
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


def _merge_user_claims(
    id_claims: dict[str, Any],
    access_claims: dict[str, Any],
) -> dict[str, Any]:
    """Fusionne les claims d'identité et d'accès pour construire le profil courant.

    Args:
        id_claims: Claims extraits de l'id token OIDC.
        access_claims: Claims extraits de l'access token OIDC.

    Returns:
        Claims utilisateur fusionnés, prêts à être stockés en session.
    """
    merged_claims = {**access_claims, **id_claims}

    for key in ["groups", "roles", "role"]:
        if not merged_claims.get(key) and access_claims.get(key):
            merged_claims[key] = access_claims[key]

    return merged_claims
