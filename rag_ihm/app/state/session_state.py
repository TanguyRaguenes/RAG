from typing import Any

import streamlit as st


CHAT_MESSAGES_KEY = "chat_messages"
CHAT_PENDING_PROMPT_KEY = "chat_pending_prompt"
DASHBOARD_RESULT_KEY = "dashboard_result"
UI_THEME_KEY = "ui_theme_mode"
UI_THEME_SYNCED_KEY = "ui_theme_synced"
UI_THEME_PERSISTED_KEY = "ui_theme_persisted"


def init_chat_state() -> None:
    st.session_state.setdefault(CHAT_MESSAGES_KEY, [])


def get_chat_messages() -> list[dict[str, Any]]:
    init_chat_state()
    return st.session_state[CHAT_MESSAGES_KEY]


def append_chat_message(message: dict[str, Any]) -> None:
    get_chat_messages().append(message)


def clear_chat_messages() -> None:
    st.session_state[CHAT_MESSAGES_KEY] = []


def set_pending_prompt(prompt: str) -> None:
    st.session_state[CHAT_PENDING_PROMPT_KEY] = prompt


def pop_pending_prompt() -> str | None:
    return st.session_state.pop(CHAT_PENDING_PROMPT_KEY, None)


def save_dashboard_result(result: dict[str, Any]) -> None:
    st.session_state[DASHBOARD_RESULT_KEY] = result


def get_dashboard_result() -> dict[str, Any] | None:
    result = st.session_state.get(DASHBOARD_RESULT_KEY)
    return result if isinstance(result, dict) else None


def clear_dashboard_result() -> None:
    st.session_state.pop(DASHBOARD_RESULT_KEY, None)


def get_theme_mode() -> str:
    value = st.session_state.get(UI_THEME_KEY, "Clair")
    return str(value)


def set_theme_mode(mode: str) -> None:
    st.session_state[UI_THEME_KEY] = mode


def has_synced_theme_preference() -> bool:
    return bool(st.session_state.get(UI_THEME_SYNCED_KEY))


def mark_theme_preference_synced(mode: str) -> None:
    st.session_state[UI_THEME_SYNCED_KEY] = True
    st.session_state[UI_THEME_PERSISTED_KEY] = mode


def get_persisted_theme_mode() -> str | None:
    value = st.session_state.get(UI_THEME_PERSISTED_KEY)

    return str(value) if value else None
