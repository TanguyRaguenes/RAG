import streamlit as st

from app.components.chat import (
    build_assistant_message,
    build_user_message,
    render_chat_message,
    render_empty_chat_state,
)
from app.components.common import (
    render_api_error,
    render_healthchecks_status,
    render_page_header,
)
from app.services.auth_service import get_access_token, require_authenticated_user
from app.services.rag_api_client import (
    RagApiError,
    ask_question,
    check_api_health,
    load_chat_api_config,
    load_evaluator_api_config,
    submit_interaction_feedback,
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


def _render_api_status(config) -> None:
    """Affiche l'état de disponibilité des APIs utilisées par la page de chat.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
    """
    healthchecks = [
        ("API RAG", lambda: check_api_health(config.health_url)),
    ]

    try:
        evaluator_config = load_evaluator_api_config()
    except RagApiError as error:
        healthchecks.append(
            ("API d'évaluation", lambda error=error: _raise_health_error(error))
        )
    else:
        healthchecks.append(
            ("API d'évaluation", lambda: check_api_health(evaluator_config.health_url))
        )

    render_healthchecks_status(healthchecks)


def _raise_health_error(error: RagApiError) -> None:
    """Convertit une erreur de healthcheck en exception affichable côté IHM.

    Args:
        error: Erreur de healthcheck ou d'appel API à convertir en message utilisateur.

    Raises:
        error: Si le traitement rencontre une erreur applicative explicitement propagée.
    """
    raise error


def _load_config_or_stop():
    """Charge la configuration requise par une page Streamlit ou arrête le rendu avec un message.

    Returns:
        Configuration de l'API chat nécessaire pour appeler l'orchestrator.
    """
    try:
        return load_chat_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _render_sidebar(config) -> tuple[str, bool]:
    """Affiche la barre latérale contextuelle de la page Streamlit courante.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.

    Returns:
        Provider sélectionné pour la réponse et indicateur d'affichage des détails techniques.
    """
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
            index=1,
            horizontal=True,
            help="À réserver au diagnostic : prompt généré et détails d'erreur.",
        )

        if st.button("🔍 État API", use_container_width=True):
            _render_api_status(config)

        if st.button("Effacer la conversation", use_container_width=True):
            clear_chat_messages()
            st.toast("Conversation effacée.")
            st.rerun()

    return PROVIDER_OPTIONS[provider_label], details_mode == "Affichés"


def _submit_feedback(config, interaction_id: int, note: int, comment: str) -> bool:
    """Envoie le feedback utilisateur associé à une interaction depuis la page de chat.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        interaction_id: Identifiant de l'interaction RAG concernée.
        note: Note utilisateur associée au feedback.
        comment: Commentaire saisi par l'utilisateur dans le formulaire de feedback.

    Returns:
        `True` si le feedback est accepté par le backend, sinon `False` après affichage de l'erreur.
    """
    try:
        submit_interaction_feedback(
            config=config,
            access_token=get_access_token(),
            interaction_id=interaction_id,
            note=note,
            commentaire=comment,
        )
    except RagApiError as error:
        render_api_error(error)
        return False

    return True


def _render_history(debug_enabled: bool, config) -> None:
    """Affiche l'historique de conversation dans la page de chat.

    Args:
        debug_enabled: Indique si les détails techniques doivent être affichés dans l'interface.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
    """
    for message in get_chat_messages():
        render_chat_message(
            message,
            debug_enabled=debug_enabled,
            on_submit_feedback=lambda interaction_id, note, comment: _submit_feedback(
                config,
                interaction_id,
                note,
                comment,
            ),
        )


def _process_prompt(prompt: str, provider: str, debug_enabled: bool, config) -> None:
    """Envoie le prompt utilisateur au RAG et ajoute la réponse à l'historique.

    Args:
        prompt: Prompt utilisateur ou prompt généré à traiter.
        provider: Provider LLM ou service externe concerné.
        debug_enabled: Indique si les détails techniques doivent être affichés dans l'interface.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
    """
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
    render_chat_message(
        assistant_message,
        debug_enabled=debug_enabled,
        on_submit_feedback=lambda interaction_id, note, comment: _submit_feedback(
            config,
            interaction_id,
            note,
            comment,
        ),
    )


config = _load_config_or_stop()
require_authenticated_user()
init_chat_state()
apply_theme()

provider, debug_mode = _render_sidebar(config)

render_page_header("IsiDore", "")

messages = get_chat_messages()
if not messages:
    render_empty_chat_state(lambda question: (set_pending_prompt(question), st.rerun()))

_render_history(debug_mode, config)

pending_prompt = pop_pending_prompt()
typed_prompt = st.chat_input("Pose ta question sur la documentation interne")
prompt = typed_prompt or pending_prompt

if prompt:
    _process_prompt(prompt, provider, debug_mode, config)
