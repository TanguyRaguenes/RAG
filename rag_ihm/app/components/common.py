from collections.abc import Callable
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


def render_healthcheck_status(label: str, healthcheck: Callable[[], None]) -> None:
    """Affiche le contrôle d'un service API."""
    render_healthchecks_status([(label, healthcheck)])


def render_healthchecks_status(
    healthchecks: list[tuple[str, Callable[[], None]]],
) -> None:
    """Affiche un contrôle lisible pour plusieurs services API."""
    results: list[tuple[str, bool, str | None]] = []

    for label, healthcheck in healthchecks:
        results.append(_run_healthcheck(label, healthcheck))

    lines = [
        f"- {label} : {'accessible' if is_available else f'inaccessible ({detail})'}"
        for label, is_available, detail in results
    ]
    all_available = all(is_available for _, is_available, _ in results)
    message = "\n".join(lines)

    if all_available:
        st.success(f"Toutes les API sont accessibles.\n\n{message}")
        st.toast("Toutes les API sont accessibles.")
        return

    st.warning(f"Certaines API sont inaccessibles.\n\n{message}")
    st.toast("Certaines API sont inaccessibles.")


def _run_healthcheck(
    label: str,
    healthcheck: Callable[[], None],
) -> tuple[str, bool, str | None]:
    try:
        healthcheck()
    except RagApiError as error:
        status_code = error.details.get("status_code")
        if status_code:
            return label, False, f"erreur HTTP {status_code}"

        return label, False, error.user_message

    return label, True, None
