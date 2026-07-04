import streamlit as st

from app.components.chat import (
    build_assistant_message,
    build_user_message,
    render_chat_message,
    render_empty_chat_state,
)
from app.components.common import (
    render_api_error,
    render_healthcheck_status,
    render_page_header,
)
from app.services.auth_service import get_access_token, require_authenticated_user
from app.services.rag_api_client import (
    RagApiError,
    ask_question,
    check_api_health,
    load_chat_api_config,
)
from app.state.session_state import (
    append_chat_message,
    clear_chat_messages,
    get_chat_messages,
    init_chat_state,
    pop_pending_prompt,
    set_pending_prompt,
)
from app.styles.theme import apply_theme


PROVIDER_OPTIONS = {
    "Cloud": "api",
    "Local": "local",
}


def _load_config_or_stop():
    try:
        return load_chat_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _render_sidebar(config) -> tuple[str, bool]:
    with st.sidebar:
        st.subheader("Discussion")

        provider_label = st.radio(
            "Mode de réponse",
            list(PROVIDER_OPTIONS.keys()),
            horizontal=True,
            help="Cloud utilise l'API configurée. Local utilise le modèle Ollama.",
        )
        details_mode = st.radio(
            "Détails techniques",
            ["Masqués", "Affichés"],
            horizontal=True,
            help="À réserver au diagnostic : prompt généré et détails d'erreur.",
        )

        if st.button("🔍 État API", use_container_width=True):
            render_healthcheck_status(
                "Ping API...",
                lambda: check_api_health(config.health_url),
            )

        if st.button("Effacer la conversation", use_container_width=True):
            clear_chat_messages()
            st.toast("Conversation effacée.")
            st.rerun()

    return PROVIDER_OPTIONS[provider_label], details_mode == "Affichés"


def _render_history(debug_enabled: bool) -> None:
    for message in get_chat_messages():
        render_chat_message(message, debug_enabled=debug_enabled)


def _process_prompt(prompt: str, provider: str, debug_enabled: bool, config) -> None:
    user_message = build_user_message(prompt)
    append_chat_message(user_message)
    render_chat_message(user_message)

    with st.spinner("Recherche dans la documentation..."):
        try:
            access_token = get_access_token()
            response = ask_question(config, prompt, provider, access_token)
        except RagApiError as error:
            render_api_error(error, debug_enabled=debug_enabled)
            return

    st.toast("Réponse prête.")

    assistant_message = build_assistant_message(response)
    append_chat_message(assistant_message)
    render_chat_message(assistant_message, debug_enabled=debug_enabled)


config = _load_config_or_stop()
require_authenticated_user()
init_chat_state()
apply_theme()

provider, debug_mode = _render_sidebar(config)

render_page_header("IsiDore", "")

messages = get_chat_messages()
if not messages:
    render_empty_chat_state(lambda question: (set_pending_prompt(question), st.rerun()))

_render_history(debug_mode)

pending_prompt = pop_pending_prompt()
typed_prompt = st.chat_input("Pose ta question sur la documentation interne")
prompt = typed_prompt or pending_prompt

if prompt:
    _process_prompt(prompt, provider, debug_mode, config)
