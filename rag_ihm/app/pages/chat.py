import streamlit as st

from app.components.chat import (
    ROLE_USER,
    build_assistant_message,
    render_chat_message,
    render_empty_chat_state,
)
from app.components.common import (
    load_config_or_stop,
    render_api_error,
    render_healthchecks_status,
    render_page_header,
)
from app.services.auth_service import get_access_token, require_authenticated_user
from app.services.rag_api_client import (
    ChatApiConfig,
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
    pop_pending_prompt,
    set_pending_prompt,
)

PROVIDER_OPTIONS = {
    "Cloud": "api",
    "Local": "local",
}


def _render_api_status(config: ChatApiConfig) -> None:
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


def _render_sidebar(config: ChatApiConfig) -> tuple[str, bool]:
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
        details_label = st.radio(
            "Détails techniques",
            ["Masqués", "Affichés"],
            index=0,
            horizontal=True,
            help="À réserver au diagnostic : sources JSON et prompt généré.",
        )

        if st.button("État API", width="stretch"):
            _render_api_status(config)

        if st.button("Effacer la conversation", width="stretch"):
            clear_chat_messages()
            st.toast("Conversation effacée.")
            st.rerun()

    return PROVIDER_OPTIONS[provider_label], details_label == "Affichés"


def _submit_feedback(
    config: ChatApiConfig,
    interaction_id: int,
    note: int,
    comment: str,
) -> bool:
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


def _render_history(
    show_technical_details: bool,
    config: ChatApiConfig,
) -> None:
    """Affiche l'historique de conversation dans la page de chat.

    Args:
        show_technical_details: Indique si les détails techniques doivent être affichés dans l'interface.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
    """
    for message in get_chat_messages():
        render_chat_message(
            message,
            debug_enabled=show_technical_details,
            on_submit_feedback=lambda interaction_id, note, comment: _submit_feedback(
                config,
                interaction_id,
                note,
                comment,
            ),
        )


def _process_prompt(
    prompt: str,
    provider: str,
    show_technical_details: bool,
    config: ChatApiConfig,
) -> None:
    """Envoie le prompt utilisateur au RAG et ajoute la réponse à l'historique.

    Args:
        prompt: Prompt utilisateur ou prompt généré à traiter.
        provider: Provider LLM ou service externe concerné.
        show_technical_details: Indique si les détails techniques doivent être affichés dans l'interface.
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
    """
    user_message = {"role": ROLE_USER, "content": prompt}
    append_chat_message(user_message)
    render_chat_message(user_message)

    with st.spinner("Recherche dans la documentation..."):
        try:
            access_token = get_access_token()
            response = ask_question(config, prompt, provider, access_token)
        except RagApiError as error:
            render_api_error(error, debug_enabled=show_technical_details)
            return

    assistant_message = build_assistant_message(response)
    append_chat_message(assistant_message)
    render_chat_message(
        assistant_message,
        debug_enabled=show_technical_details,
        on_submit_feedback=lambda interaction_id, note, comment: _submit_feedback(
            config,
            interaction_id,
            note,
            comment,
        ),
    )


def _select_example_question(question: str) -> None:
    """Place une question d'exemple dans la file du prochain rendu.

    Args:
        question: Exemple sélectionné par l'utilisateur.
    """
    set_pending_prompt(question)
    st.rerun()


config = load_config_or_stop(load_chat_api_config)
require_authenticated_user()

provider, show_technical_details = _render_sidebar(config)

render_page_header("IsiDore", "")

messages = get_chat_messages()
examples_placeholder = st.empty()
if not messages:
    with examples_placeholder.container():
        render_empty_chat_state(_select_example_question)

_render_history(show_technical_details, config)

pending_prompt = pop_pending_prompt()
typed_prompt = st.chat_input("Pose ta question sur la documentation interne")
prompt = typed_prompt or pending_prompt

if prompt:
    examples_placeholder.empty()
    _process_prompt(prompt, provider, show_technical_details, config)
