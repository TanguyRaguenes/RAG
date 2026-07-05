from typing import Any

import streamlit as st


ROLE_ASSISTANT = "assistant"
ROLE_USER = "user"
FEEDBACK_STATE_PREFIX = "chat_feedback_"
FEEDBACK_TOAST_PREFIX = "chat_feedback_toast_"


EXAMPLE_QUESTIONS = [
    "Comment fonctionne l'architecture microservices ?",
    "Quels sont les prérequis d'installation ?",
    "Où trouver la procédure de déploiement ?",
]


def render_empty_chat_state(on_select_question) -> None:
    """Affiche l'état vide du chat avec des exemples actionnables."""
    st.caption("Exemples pour commencer")
    columns = st.columns(len(EXAMPLE_QUESTIONS))
    for column, question in zip(columns, EXAMPLE_QUESTIONS):
        with column:
            if st.button(question, use_container_width=True):
                on_select_question(question)


def build_user_message(content: str) -> dict[str, Any]:
    return {"role": ROLE_USER, "content": content}


def build_assistant_message(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": ROLE_ASSISTANT,
        "interaction_id": response.get("interaction_id"),
        "content": response.get("llm_response", "Pas de réponse générée."),
        "retrieved_documents": response.get("retrieved_documents") or {},
        "retrieved_chunks": response.get("retrieved_chunks") or [],
        "model": response.get("model"),
        "duration": response.get("duration"),
        "total_tokens": response.get("total_tokens"),
        "cost": response.get("cost"),
        "generated_prompt": response.get("generated_prompt"),
    }


def render_chat_message(
    message: dict[str, Any],
    debug_enabled: bool = False,
    on_submit_feedback=None,
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
        _render_sources(message.get("retrieved_chunks"), debug_enabled=debug_enabled)

        if debug_enabled and message.get("generated_prompt"):
            with st.expander("Prompt généré"):
                st.json(message["generated_prompt"])

        if on_submit_feedback:
            _render_feedback_form(message, on_submit_feedback)


def _render_assistant_metadata(message: dict[str, Any]) -> None:
    metadata = []
    if message.get("model"):
        metadata.append(str(message["model"]))
    if message.get("duration"):
        metadata.append(str(message["duration"]))
    if message.get("total_tokens"):
        metadata.append(f"{message['total_tokens']} tokens")
    if message.get("cost"):
        metadata.append(f"{message['cost']} EUR")

    if metadata:
        st.caption(" | ".join(metadata))


def _render_source_summary(documents: Any) -> None:
    if not isinstance(documents, dict) or not documents:
        return

    with st.expander(f"Sources consultées ({len(documents)})"):
        for title, count in documents.items():
            st.markdown(f"- **{title}** : {count} extrait(s)")


def _render_sources(chunks: Any, debug_enabled: bool) -> None:
    if not isinstance(chunks, list) or not chunks:
        st.caption("Aucune source détaillée retournée par le RAG.")
        return

    with st.expander(f"Extraits pertinents ({len(chunks)})"):
        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            title = metadata.get("title") or metadata.get("path") or "Source inconnue"
            similarity = chunk.get("similarity") if isinstance(chunk, dict) else None
            document = chunk.get("document", "") if isinstance(chunk, dict) else ""
            excerpt = _shorten_text(str(document), limit=700)
            score = _format_similarity(similarity) if similarity is not None else None

            line = f"[{index}] {title}"
            if score:
                line = f"{line} · score {score}"
            st.markdown(f"**{line}**")
            if excerpt:
                st.markdown(excerpt)
            if index < len(chunks):
                st.divider()

        if debug_enabled:
            st.json(chunks)


def _render_feedback_form(message: dict[str, Any], on_submit_feedback) -> None:
    interaction_id = message.get("interaction_id")
    if not interaction_id:
        return

    feedback_key = f"{FEEDBACK_STATE_PREFIX}{interaction_id}"
    toast_key = f"{FEEDBACK_TOAST_PREFIX}{interaction_id}"
    feedback = st.session_state.get(feedback_key) or message.get("feedback")

    if st.session_state.pop(toast_key, False):
        st.toast("Avis envoyé.")

    st.caption("Cette réponse t'a-t-elle aidé ?")
    comment_column, vote_column = st.columns([5, 1])

    with comment_column:
        comment = st.text_area(
            "Commentaire optionnel",
            value=str(feedback.get("commentaire") or "") if feedback else "",
            max_chars=2000,
            height=88,
            key=f"feedback_comment_{interaction_id}",
        )

    with vote_column:
        liked = feedback and feedback.get("note") == 1
        disliked = feedback and feedback.get("note") == -1
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


def _shorten_text(text: str, limit: int = 700) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _format_similarity(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "non disponible"
