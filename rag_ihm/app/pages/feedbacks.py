from datetime import date, timedelta

import streamlit as st

from app.components.common import render_api_error, render_page_header
from app.services.auth_service import (
    get_access_token,
    is_usage_admin,
    require_authenticated_user,
)
from app.services.rag_api_client import (
    RagApiError,
    list_admin_interaction_feedbacks,
    load_chat_api_config,
)
from app.styles.theme import apply_theme


def _load_config_or_stop():
    """Charge la configuration requise par une page Streamlit ou arrête le rendu avec un message.

    Returns:
        Configuration de l'API chat utilisée pour interroger les endpoints d'administration.
    """
    try:
        return load_chat_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _render_period_selector() -> tuple[date, date]:
    """Affiche le sélecteur de période utilisé pour filtrer les feedbacks.

    Returns:
        Dates de début et de fin choisies pour filtrer les feedbacks affichés.
    """
    today = date.today()
    default_start = today - timedelta(days=7)

    start_column, end_column = st.columns(2)
    with start_column:
        start_date = st.date_input("Début", value=default_start)
    with end_column:
        end_date = st.date_input("Fin", value=today)

    return start_date, end_date


def _load_feedbacks(config, access_token: str | None, start_date: date, end_date: date):
    """Charge les feedbacks administrateur pour la période sélectionnée.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
        start_date: Date de début du filtre de période.
        end_date: Date de fin du filtre de période.

    Returns:
        Liste de feedbacks chargés pour la période demandée.
    """
    with st.spinner("Chargement des avis..."):
        try:
            return list_admin_interaction_feedbacks(
                config,
                access_token,
                start_date,
                end_date,
            )
        except RagApiError as error:
            render_api_error(error, debug_enabled=True)
            return []


def _feedback_to_table_row(feedback: dict) -> dict:
    """Transforme un feedback brut en ligne de tableau Streamlit.

    Args:
        feedback: Feedback brut d'interaction à convertir pour l'affichage administrateur.

    Returns:
        Ligne de tableau représentant un feedback d'interaction.
    """
    return {
        "Date": _format_date(feedback.get("cree_le")),
        "Question": feedback.get("question") or "-",
        "Réponse LLM": feedback.get("reponse") or "-",
        "Documents / chunks": _format_chunks(feedback.get("chunks")),
        "Avis": _format_note(feedback.get("note")),
        "Commentaire": feedback.get("commentaire") or "-",
    }


def _format_date(value: object) -> str:
    """Formate une date ou un timestamp pour l'affichage des feedbacks.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Date formatée ou valeur de remplacement si elle est absente.
    """
    if not value:
        return "-"

    return str(value).replace("T", " ")[:19]


def _format_note(value: object) -> str:
    """Formate une note de feedback avec une valeur de remplacement si elle manque.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Note formatée ou valeur de remplacement si elle manque.
    """
    if value == 1:
        return "Like"
    if value == -1:
        return "Dislike"

    return "-"


def _format_chunks(chunks: object) -> str:
    """Formate la liste de chunks associés à une interaction pour l'affichage.

    Args:
        chunks: Chunks documentaires manipulés par le pipeline RAG.

    Returns:
        Résumé textuel des chunks associés à une interaction.
    """
    if not isinstance(chunks, list) or not chunks:
        return "-"

    formatted_chunks = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        rank = chunk.get("rang") or "?"
        title = chunk.get("titre") or "Document inconnu"
        path = chunk.get("chemin") or "-"
        score = chunk.get("score")
        content = str(chunk.get("contenu") or "").strip()
        score_label = f" - score {float(score):.2f}" if score is not None else ""
        formatted_chunks.append(f"[{rank}] {title}{score_label}\n{path}\n{content}")

    return "\n\n".join(formatted_chunks) if formatted_chunks else "-"


config = _load_config_or_stop()
current_user = require_authenticated_user()
access_token = get_access_token()

apply_theme()

if not is_usage_admin(current_user):
    st.error("Cette page est réservée aux administrateurs.")
    st.stop()

render_page_header(
    "Avis utilisateurs",
    "Consulte les questions, réponses et avis sur une période.",
)

start_date, end_date = _render_period_selector()

if end_date < start_date:
    st.warning("La date de fin doit être postérieure ou égale à la date de début.")
    st.stop()

feedbacks = _load_feedbacks(config, access_token, start_date, end_date)

if not feedbacks:
    st.info("Aucune question trouvée sur cette période.")
    st.stop()

table_rows = [_feedback_to_table_row(feedback) for feedback in feedbacks]
st.markdown('<div class="dataframe-toolbar-safe-space"></div>', unsafe_allow_html=True)
st.dataframe(table_rows, use_container_width=True, hide_index=True)
