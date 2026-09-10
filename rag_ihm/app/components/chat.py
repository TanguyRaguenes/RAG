import math
from collections.abc import Callable

import streamlit as st

from app.schemas.api import AskQuestionResponse, ChatMessage

ROLE_ASSISTANT = "assistant"
ROLE_USER = "user"
FEEDBACK_STATE_PREFIX = "chat_feedback_"
FEEDBACK_TOAST_PREFIX = "chat_feedback_toast_"


EXAMPLE_QUESTIONS = [
    "Quelles sont les bonnes pratiques pour un développeur ?",
    "Comment rédiger un commentaire ?",
    "Donne moi les noms et url des VM ?",
]


QuestionSelectionCallback = Callable[[str], None]
FeedbackCallback = Callable[[int, int, str], bool]


def render_empty_chat_state(on_select_question: QuestionSelectionCallback) -> None:
    """Affiche l'état vide du chat avec des exemples actionnables."""
    st.caption("Exemples pour commencer")
    columns = st.columns(len(EXAMPLE_QUESTIONS))
    for column, question in zip(columns, EXAMPLE_QUESTIONS):
        with column:
            if st.button(question, width="stretch"):
                on_select_question(question)


def build_assistant_message(response: AskQuestionResponse) -> ChatMessage:
    """Construit le modèle de message affiché pour une réponse RAG.

    Args:
        response: Réponse HTTP ou objet de réponse à décoder.

    Returns:
        Message assistant enrichi avec réponse, sources et métadonnées.
    """
    return {
        "role": ROLE_ASSISTANT,
        "interaction_id": response.get("interaction_id"),
        "content": response.get("llm_response", "Pas de réponse générée."),
        "retrieved_documents": response.get("retrieved_documents") or {},
        "retrieved_chunks": response.get("retrieved_chunks") or [],
        "model": response.get("model"),
        "duration": response.get("duration"),
        "total_tokens": response.get("total_tokens"),
        "generated_prompt": response.get("generated_prompt"),
        "chunking_enabled": response.get("chunking_enabled"),
        "use_reranker": response.get("use_reranker"),
    }


def render_chat_message(
    message: ChatMessage,
    debug_enabled: bool = False,
    on_submit_feedback: FeedbackCallback | None = None,
) -> None:
    """Affiche un message de chat et les informations assistant associées."""
    role = str(message.get("role", ROLE_ASSISTANT))
    content = str(message.get("content", ""))

    with st.chat_message(role):
        st.markdown(content)

        if role != ROLE_ASSISTANT:
            return

        _render_assistant_metadata(message)
        _render_source_summary(message.get("retrieved_documents"))
        if debug_enabled:
            _render_pipeline_configuration(message)
        _render_sources(
            message.get("retrieved_chunks"),
            debug_enabled=debug_enabled,
            use_reranker=message.get("use_reranker", True),
        )

        if debug_enabled and message.get("generated_prompt"):
            with st.expander("Prompt généré"):
                _render_generated_prompt(message["generated_prompt"])
            with st.expander("Prompt généré - JSON"):
                st.json(message["generated_prompt"])

        if on_submit_feedback:
            _render_feedback_form(message, on_submit_feedback)


def _render_assistant_metadata(message: ChatMessage) -> None:
    """Affiche les métadonnées techniques d'une réponse assistant dans Streamlit.

    Args:
        message: Réponse assistant contenant les champs techniques optionnels à afficher.
    """
    metadata = []
    if message.get("model"):
        metadata.append(str(message["model"]))
    if message.get("duration"):
        metadata.append(str(message["duration"]))
    if message.get("total_tokens"):
        metadata.append(f"{message['total_tokens']} tokens")

    if metadata:
        st.caption(" | ".join(metadata))


def _render_generated_prompt(generated_prompt: object) -> None:
    """Affiche le prompt généré dans une zone dépliable de diagnostic.

    Args:
        generated_prompt: Prompt construit par l'orchestrator et affichable en mode diagnostic.
    """
    if not isinstance(generated_prompt, list):
        st.json(generated_prompt)
        return

    for index, prompt_message in enumerate(generated_prompt, start=1):
        if not isinstance(prompt_message, dict):
            st.json(prompt_message)
            continue

        role = prompt_message.get("role", f"message {index}")
        content = prompt_message.get("content", "")

        st.markdown(f"**{role}**")
        st.markdown(str(content))


def _render_source_summary(documents: object) -> None:
    """Affiche le résumé des documents sources utilisés par la réponse.

    Args:
        documents: Contenus textuels retournés par ChromaDB ou à ingérer.
    """
    if not isinstance(documents, dict) or not documents:
        return

    with st.expander(f"Sources consultées ({len(documents)})"):
        for title, count in documents.items():
            st.markdown(f"- **{title}** : {count} extrait(s)")


def _render_pipeline_configuration(message: ChatMessage) -> None:
    """Affiche les paramètres actifs du pipeline pour la réponse."""
    with st.expander("Paramétrage"):
        st.markdown(
            f"- Chunking : **{_format_activation(message.get('chunking_enabled'))}**\n"
            f"- Reranking : **{_format_activation(message.get('use_reranker'))}**"
        )


def _render_sources(
    chunks: object,
    debug_enabled: bool,
    use_reranker: bool = True,
) -> None:
    """Affiche le détail des chunks sources associés à une réponse.

    Args:
        chunks: Chunks documentaires manipulés par le pipeline RAG.
        debug_enabled: Indique si les détails techniques doivent être affichés dans l'interface.
        use_reranker: Indique si les chunks ont été rerankés.
    """
    if not isinstance(chunks, list) or not chunks:
        st.caption("Le RAG n'a retourné aucune source.")
        return

    sorted_chunks = _sort_chunks_by_rerank_score(chunks) if use_reranker else chunks

    with st.expander(f"Extraits pertinents ({len(sorted_chunks)})"):
        for index, chunk in enumerate(sorted_chunks, start=1):
            _render_source_chunk(
                index,
                chunk,
                use_reranker=use_reranker,
                show_divider=index < len(sorted_chunks),
            )

    if debug_enabled:
        with st.expander(f"Extraits pertinents - JSON ({len(sorted_chunks)})"):
            st.json(sorted_chunks)


def _render_source_chunk(
    index: int,
    chunk: object,
    *,
    use_reranker: bool,
    show_divider: bool,
) -> None:
    """Affiche un extrait documentaire et ses scores dans la liste des sources.

    Args:
        index: Rang d'affichage du chunk.
        chunk: Chunk brut retourné par le pipeline RAG.
        use_reranker: Indique si le score de reranking doit être affiché.
        show_divider: Ajoute un séparateur après le chunk courant.
    """
    chunk_data = chunk if isinstance(chunk, dict) else {}
    metadata = chunk_data.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    title = metadata.get("title") or metadata.get("path") or "Source inconnue"
    retriever_score = chunk_data.get("similarity")

    if use_reranker:
        line = (
            f"[{index}] {title} · score reranker "
            f"{_format_score(chunk_data.get('rerank_score'))} "
            f"(score retriever {_format_score(retriever_score)})"
        )
    else:
        line = f"[{index}] {title} · score retriever {_format_score(retriever_score)}"

    st.markdown(f"**{line}**")
    excerpt = _shorten_text(str(chunk_data.get("document", "")), limit=700)
    if excerpt:
        st.markdown(excerpt)
    if show_divider:
        st.divider()


def _render_feedback_form(
    message: ChatMessage,
    on_submit_feedback: FeedbackCallback,
) -> None:
    """Affiche le formulaire de feedback lié à une interaction RAG.

    Args:
        message: Réponse assistant contenant l'identifiant d'interaction lié au feedback.
        on_submit_feedback: Callback appelé lorsque l'utilisateur soumet un feedback.
    """
    interaction_id = message.get("interaction_id")
    if not interaction_id:
        return

    feedback_key = f"{FEEDBACK_STATE_PREFIX}{interaction_id}"
    toast_key = f"{FEEDBACK_TOAST_PREFIX}{interaction_id}"
    feedback = st.session_state.get(feedback_key) or message.get("feedback")

    if st.session_state.pop(toast_key, False):
        st.toast("Avis envoyé.")

    comment, like_submitted, dislike_submitted = _render_feedback_controls(
        interaction_id, feedback
    )

    if not like_submitted and not dislike_submitted:
        return

    note = 1 if like_submitted else -1
    if not on_submit_feedback(int(interaction_id), note, comment):
        return

    feedback_value = {"note": note, "commentaire": comment.strip() or None}
    message["feedback"] = feedback_value
    st.session_state[feedback_key] = feedback_value
    st.session_state[toast_key] = True
    st.rerun()


def _render_feedback_controls(
    interaction_id: object,
    feedback: object,
) -> tuple[str, bool, bool]:
    """Affiche les champs de saisie d'un avis et retourne les actions utilisateur.

    Args:
        interaction_id: Identifiant utilisé pour stabiliser les clés Streamlit.
        feedback: Avis déjà enregistré et éventuellement réaffiché.

    Returns:
        Commentaire saisi et état des deux boutons de vote.
    """
    feedback_data = feedback if isinstance(feedback, dict) else {}
    st.caption("Cette réponse t'a-t-elle aidé ?")
    comment_column, vote_column = st.columns([5, 1])

    with comment_column:
        comment = st.text_area(
            "Commentaire optionnel",
            value=str(feedback_data.get("commentaire") or ""),
            max_chars=2000,
            height=88,
            key=f"feedback_comment_{interaction_id}",
        )

    with vote_column:
        liked = feedback_data.get("note") == 1
        disliked = feedback_data.get("note") == -1
        like_submitted = st.button(
            "👍",
            key=f"feedback_like_{interaction_id}_{'selected' if liked else 'idle'}",
            type="primary" if liked else "secondary",
        )
        dislike_submitted = st.button(
            "👎",
            key=f"feedback_dislike_{interaction_id}_{'selected' if disliked else 'idle'}",
            type="primary" if disliked else "secondary",
        )

    return comment, like_submitted, dislike_submitted


def _shorten_text(text: str, limit: int = 700) -> str:
    """Tronque un texte long pour l'affichage compact dans l'IHM.

    Args:
        text: Texte à analyser, formater ou afficher.
        limit: Nombre maximal de caractères conservés.

    Returns:
        Texte raccourci à la longueur maximale demandée.
    """
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _sort_chunks_by_rerank_score(chunks: list[object]) -> list[object]:
    """Trie les extraits par score reranker décroissant, sans perdre les invalides."""

    def score(chunk: object) -> float:
        if not isinstance(chunk, dict):
            return float("-inf")
        try:
            value = float(chunk.get("rerank_score"))
        except (TypeError, ValueError):
            return float("-inf")
        return value if math.isfinite(value) else float("-inf")

    return sorted(chunks, key=score, reverse=True)


def _format_score(value: object) -> str:
    """Formate un score de pertinence pour l'affichage utilisateur.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Score formaté ou indication de valeur indisponible.
    """
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "non disponible"


def _format_activation(value: object) -> str:
    """Formate l'état d'activation d'un paramètre technique."""
    if not isinstance(value, bool):
        return "non disponible"
    return "activé" if value else "désactivé"
