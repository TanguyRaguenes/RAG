import base64
import html
import json
import os
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
import streamlit as st


ACCESS_TOKEN_KEY = "auth_access_token"
ID_TOKEN_KEY = "auth_id_token"
REFRESH_TOKEN_KEY = "auth_refresh_token"
USER_KEY = "auth_user"
STATE_KEY = "auth_state"


@dataclass(frozen=True)
class OidcConfig:
    authorize_url: str
    token_url: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        st.error(f"Variable d'environnement manquante : {name}")
        st.stop()

    return value


def get_oidc_config() -> OidcConfig:
    return OidcConfig(
        authorize_url=_get_required_env("RAG_IHM_OIDC_AUTHORIZE_URL"),
        token_url=_get_required_env("RAG_IHM_OIDC_TOKEN_URL"),
        client_id=_get_required_env("RAG_IHM_OIDC_CLIENT_ID"),
        client_secret=_get_required_env("RAG_IHM_OIDC_CLIENT_SECRET"),
        redirect_uri=_get_required_env("RAG_IHM_OIDC_REDIRECT_URI"),
        scope=os.getenv("RAG_IHM_OIDC_SCOPE", "openid email profile groups"),
    )


def is_authenticated() -> bool:
    return bool(st.session_state.get(ACCESS_TOKEN_KEY))


def get_access_token() -> str | None:
    return st.session_state.get(ACCESS_TOKEN_KEY)


def get_current_user() -> dict[str, Any] | None:
    return st.session_state.get(USER_KEY)


def logout() -> None:
    for key in [ACCESS_TOKEN_KEY, ID_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_KEY, STATE_KEY]:
        st.session_state.pop(key, None)


def build_login_url() -> str:
    config = get_oidc_config()
    state = secrets.token_urlsafe(32)
    st.session_state[STATE_KEY] = state

    params = {
        "response_type": "code",
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scope,
        "state": state,
    }

    return f"{config.authorize_url}?{urlencode(params)}"


def _query_param_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None

    return value


def _decode_jwt_payload_without_verification(token: str) -> dict[str, Any]:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded_payload = base64.urlsafe_b64decode(payload.encode("utf-8"))
        return json.loads(decoded_payload)
    except Exception:
        return {}


def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
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
    error = _query_param_value("error")
    if error:
        st.error(f"Authentification refusée par Pocket ID : {error}")
        st.stop()

    code = _query_param_value("code")
    if not code:
        return

    returned_state = _query_param_value("state")
    expected_state = st.session_state.get(STATE_KEY)
    if expected_state and returned_state != expected_state:
        logout()
        st.error("État OAuth invalide. Recommence la connexion.")
        st.stop()

    try:
        token_response = _exchange_code_for_tokens(code)
    except requests.HTTPError as exception:
        status_code = (
            exception.response.status_code if exception.response is not None else "?"
        )
        response_text = (
            exception.response.text if exception.response is not None else str(exception)
        )
        st.error(f"Échec de l'échange OAuth : {status_code} - {response_text}")
        st.stop()
    except requests.RequestException as exception:
        st.error(f"Impossible de contacter Pocket ID : {exception}")
        st.stop()

    access_token = token_response.get("access_token")
    if not access_token:
        st.error("Pocket ID n'a pas retourné d'access_token.")
        st.stop()

    st.session_state[ACCESS_TOKEN_KEY] = access_token
    st.session_state[ID_TOKEN_KEY] = token_response.get("id_token")
    st.session_state[REFRESH_TOKEN_KEY] = token_response.get("refresh_token")
    st.session_state[USER_KEY] = _decode_jwt_payload_without_verification(
        token_response.get("id_token", "")
    )

    st.query_params.clear()
    st.rerun()


def require_authenticated_user() -> dict[str, Any] | None:
    if is_authenticated():
        return get_current_user()

    from app.styles.theme import apply_theme, render_theme_selector

    apply_theme()

    with st.sidebar:
        render_theme_selector()

    login_url = html.escape(build_login_url(), quote=True)
    st.markdown(
        f"""
        <div class="auth-shell">
            <div class="auth-card">
                <div class="auth-eyebrow">RAG interne</div>
                <div class="auth-title">IsiDore</div>
                <div class="auth-copy">
                    Connecte-toi avec Pocket ID pour accéder à la documentation interne.
                </div>
                <a class="auth-button" href="{login_url}">Se connecter avec Pocket ID</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()
