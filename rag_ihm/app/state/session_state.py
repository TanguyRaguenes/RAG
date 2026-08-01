import streamlit as st

from app.schemas.api import ChatMessage, EvaluationResponse

CHAT_MESSAGES_KEY = "chat_messages"
CHAT_PENDING_PROMPT_KEY = "chat_pending_prompt"
DASHBOARD_RESULT_KEY = "dashboard_result"


def get_chat_messages() -> list[ChatMessage]:
    """Retourne l'historique de messages stocké dans la session Streamlit.

    Returns:
        Liste mutable des messages de chat conservés en session Streamlit.
    """
    return st.session_state.setdefault(CHAT_MESSAGES_KEY, [])


def append_chat_message(message: ChatMessage) -> None:
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


def save_dashboard_result(result: EvaluationResponse) -> None:
    """Mémorise le dernier résultat d'évaluation affiché dans le dashboard.

    Args:
        result: Résultat d'évaluation ou de dashboard à stocker en session.
    """
    st.session_state[DASHBOARD_RESULT_KEY] = result


def get_dashboard_result() -> EvaluationResponse | None:
    """Retourne le dernier résultat d'évaluation conservé en session.

    Returns:
        Dernier résultat d'évaluation stocké en session, ou `None`.
    """
    result = st.session_state.get(DASHBOARD_RESULT_KEY)
    return result if isinstance(result, dict) else None


def clear_dashboard_result() -> None:
    """Supprime le résultat d'évaluation conservé en session."""
    st.session_state.pop(DASHBOARD_RESULT_KEY, None)
