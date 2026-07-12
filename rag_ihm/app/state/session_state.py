from typing import Any

import streamlit as st


CHAT_MESSAGES_KEY = "chat_messages"
CHAT_PENDING_PROMPT_KEY = "chat_pending_prompt"
DASHBOARD_RESULT_KEY = "dashboard_result"
UI_THEME_KEY = "ui_theme_mode"
UI_THEME_SYNCED_KEY = "ui_theme_synced"
UI_THEME_PERSISTED_KEY = "ui_theme_persisted"


def init_chat_state() -> None:
    """Initialise les clés Streamlit nécessaires à l'historique de conversation."""
    st.session_state.setdefault(CHAT_MESSAGES_KEY, [])


def get_chat_messages() -> list[dict[str, Any]]:
    """Retourne l'historique de messages stocké dans la session Streamlit.

    Returns:
        Liste mutable des messages de chat conservés en session Streamlit.
    """
    init_chat_state()
    return st.session_state[CHAT_MESSAGES_KEY]


def append_chat_message(message: dict[str, Any]) -> None:
    """Ajoute un message utilisateur ou assistant à l'historique Streamlit.

    Args:
        message: Message utilisateur ou assistant à conserver dans l'historique de conversation.
    """
    get_chat_messages().append(message)


def clear_chat_messages() -> None:
    """Vide l'historique de conversation de la session Streamlit."""
    st.session_state[CHAT_MESSAGES_KEY] = []


def set_pending_prompt(prompt: str) -> None:
    """Stocke temporairement un prompt à traiter lors du prochain rendu Streamlit.

    Args:
        prompt: Prompt utilisateur ou prompt généré à traiter.
    """
    st.session_state[CHAT_PENDING_PROMPT_KEY] = prompt


def pop_pending_prompt() -> str | None:
    """Récupère puis supprime le prompt en attente de traitement.

    Returns:
        Prompt en attente, ou `None` si aucun prompt n'était stocké.
    """
    return st.session_state.pop(CHAT_PENDING_PROMPT_KEY, None)


def save_dashboard_result(result: dict[str, Any]) -> None:
    """Mémorise le dernier résultat d'évaluation affiché dans le dashboard.

    Args:
        result: Résultat d'évaluation ou de dashboard à stocker en session.
    """
    st.session_state[DASHBOARD_RESULT_KEY] = result


def get_dashboard_result() -> dict[str, Any] | None:
    """Retourne le dernier résultat d'évaluation conservé en session.

    Returns:
        Dernier résultat d'évaluation stocké en session, ou `None`.
    """
    result = st.session_state.get(DASHBOARD_RESULT_KEY)
    return result if isinstance(result, dict) else None


def clear_dashboard_result() -> None:
    """Supprime le résultat d'évaluation conservé en session."""
    st.session_state.pop(DASHBOARD_RESULT_KEY, None)


def get_theme_mode() -> str:
    """Retourne le mode de thème actuellement sélectionné dans la session.

    Returns:
        Nom du thème actuellement actif dans l'IHM.
    """
    value = st.session_state.get(UI_THEME_KEY, "Clair")
    return str(value)


def set_theme_mode(mode: str) -> None:
    """Enregistre le mode de thème choisi dans la session Streamlit.

    Args:
        mode: Mode de thème sélectionné par l'utilisateur.
    """
    st.session_state[UI_THEME_KEY] = mode


def has_synced_theme_preference() -> bool:
    """Indique si la préférence de thème distante a déjà été synchronisée.

    Returns:
        `True` si la préférence de thème a déjà été synchronisée.
    """
    return bool(st.session_state.get(UI_THEME_SYNCED_KEY))


def mark_theme_preference_synced(mode: str) -> None:
    """Marque la préférence de thème comme synchronisée avec la valeur distante.

    Args:
        mode: Mode de thème sélectionné par l'utilisateur.
    """
    st.session_state[UI_THEME_SYNCED_KEY] = True
    st.session_state[UI_THEME_PERSISTED_KEY] = mode


def get_persisted_theme_mode() -> str | None:
    """Retourne le thème précédemment persisté pour éviter les écritures inutiles.

    Returns:
        Nom du thème déjà persisté, ou `None` si aucune valeur n'est connue.
    """
    value = st.session_state.get(UI_THEME_PERSISTED_KEY)

    return str(value) if value else None
