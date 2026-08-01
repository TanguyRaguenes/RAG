import logging
from collections.abc import Callable

import streamlit as st

from app.core.errors import RagApiError
from app.schemas.api import AuthenticatedUser
from app.services.auth_service import is_evaluator_admin, is_usage_admin

logger = logging.getLogger(__name__)


def load_config_or_stop[Config](loader: Callable[[], Config]) -> Config:
    """Charge une configuration ou interrompt proprement le rendu de la page."""
    try:
        return loader()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def render_sidebar_header(current_user: AuthenticatedUser | None) -> None:
    """Affiche l'application et l'utilisateur connecté dans la barre latérale."""
    st.title("IsiDore")
    st.caption("Assistant RAG sur la documentation interne ISILOG.")

    user_label = None
    if current_user:
        user_label = current_user.get("email") or current_user.get("name")

    if user_label:
        st.caption(f"Connecté : {user_label}")

    if is_usage_admin(current_user) or is_evaluator_admin(current_user):
        st.success("Profil administrateur")


def render_page_header(title: str, subtitle: str) -> None:
    """Affiche un en-tête homogène pour les pages Streamlit."""
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def render_api_error(error: RagApiError, debug_enabled: bool = False) -> None:
    """Journalise puis affiche une erreur API depuis un point Streamlit unique.

    Args:
        error: Erreur dont le corps backend a déjà été écarté.
        debug_enabled: Paramètre conservé pour les callbacks Streamlit existants.
    """
    if error.status_code == 401:
        st.session_state.clear()

    level = (
        logging.WARNING
        if error.retryable
        or (error.status_code is not None and error.status_code < 500)
        else logging.ERROR
    )
    logger.log(
        level,
        "RAG API operation failed",
        extra={
            "service": "rag_ihm",
            "event": "rag_api_error",
            "error_code": error.code,
            "retryable": error.retryable,
            "details": error.safe_details,
        },
    )
    st.error(error.user_message)


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
        return

    st.warning(f"Certaines API sont inaccessibles.\n\n{message}")


def _run_healthcheck(
    label: str,
    healthcheck: Callable[[], None],
) -> tuple[str, bool, str | None]:
    """Exécute un healthcheck et retourne son libellé, son état et son erreur."""
    try:
        healthcheck()
    except RagApiError as error:
        _log_healthcheck_error(error)
        status_code = error.details.get("status_code")
        if status_code:
            return label, False, f"erreur HTTP {status_code}"

        return label, False, error.user_message

    return label, True, None


def _log_healthcheck_error(error: RagApiError) -> None:
    """Journalise un healthcheck échoué sans créer un second message visuel.

    Args:
        error: Erreur API déjà assainie par le client HTTP.
    """
    level = logging.WARNING if error.retryable else logging.ERROR
    logger.log(
        level,
        "RAG API healthcheck failed",
        extra={
            "service": "rag_ihm",
            "event": "rag_api_healthcheck_error",
            "error_code": error.code,
            "retryable": error.retryable,
            "details": error.safe_details,
        },
    )
