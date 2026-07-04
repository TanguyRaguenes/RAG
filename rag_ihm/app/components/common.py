from pathlib import Path
from typing import Any

import streamlit as st

from app.services.auth_service import is_usage_admin
from app.services.rag_api_client import RagApiError


def render_sidebar_brand(current_user: dict[str, Any] | None) -> None:
    """Affiche l'identité de l'application et l'utilisateur connecté."""
    image_path = Path("assets/images/robot_isilog.png")
    if image_path.exists():
        st.image(str(image_path), use_container_width=True)
    else:
        st.title("IsiDore")

    st.caption("Assistant RAG sur la documentation interne ISILOG.")

    user_label = None
    if current_user:
        user_label = current_user.get("email") or current_user.get("name")

    if user_label:
        st.caption(f"Connecté : {user_label}")

    if is_usage_admin(current_user):
        st.success("Profil administrateur")


def render_page_header(title: str, subtitle: str) -> None:
    """Affiche un en-tête homogène pour les pages Streamlit."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_api_error(error: RagApiError, debug_enabled: bool = False) -> None:
    """Affiche une erreur API lisible, avec détails masqués si demandé."""
    st.error(error.user_message)
    if debug_enabled and error.details:
        with st.expander("Détails techniques"):
            st.json(error.details)


def render_healthcheck_status(label: str, healthcheck) -> None:
    """Affiche le contrôle API sans bloc persistant dans la sidebar."""
    try:
        healthcheck()
    except RagApiError as error:
        status_code = error.details.get("status_code")
        if status_code:
            st.toast(f"Erreur API ({status_code})")
        else:
            st.toast("Serveur injoignable")
    else:
        st.toast("Connecté")
