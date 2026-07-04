import streamlit as st

from app.components.common import render_sidebar_brand
from app.services.auth_service import (
    get_access_token,
    get_current_user,
    handle_oidc_callback,
    is_authenticated,
    logout,
)
from app.services.rag_api_client import RagApiError, load_chat_api_config
from app.styles.theme import apply_theme, render_theme_selector, sync_theme_preference

st.set_page_config(page_title="IsiDore", layout="wide")

handle_oidc_callback()


def _load_chat_config_or_none():
    try:
        return load_chat_api_config()
    except RagApiError:
        return None


def _render_global_sidebar(config) -> None:
    current_user = get_current_user()
    access_token = get_access_token()

    with st.sidebar:
        render_sidebar_brand(current_user)
        st.divider()
        render_theme_selector(config, access_token)
        st.divider()

        if st.button("Se déconnecter", use_container_width=True):
            logout()
            st.rerun()


chat_config = _load_chat_config_or_none() if is_authenticated() else None

if is_authenticated() and chat_config is not None:
    sync_theme_preference(chat_config, get_access_token())

apply_theme()

if is_authenticated() and chat_config is not None:
    _render_global_sidebar(chat_config)

pages = [
    st.Page("pages/chat.py", title="Discussion", default=True),
    st.Page("pages/usage.py", title="Consommation"),
    st.Page("pages/dashboard.py", title="Évaluation"),
]

pg = st.navigation(pages)
pg.run()
