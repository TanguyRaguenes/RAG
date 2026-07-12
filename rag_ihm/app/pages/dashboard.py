import streamlit as st

from app.components.common import (
    render_api_error,
    render_page_header,
)
from app.components.dashboard import (
    render_answer_scores,
    render_dashboard_empty_state,
    render_retrieval_scores,
    render_summary_cards,
)
from app.services.auth_service import is_usage_admin, require_authenticated_user
from app.services.rag_api_client import (
    RagApiError,
    load_evaluator_api_config,
    run_evaluation,
)
from app.state.session_state import (
    clear_dashboard_result,
    get_dashboard_result,
    save_dashboard_result,
)
from app.styles.theme import apply_theme


def _load_evaluator_config_or_stop():
    try:
        return load_evaluator_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _render_sidebar() -> None:
    with st.sidebar:
        has_result = get_dashboard_result() is not None
        if has_result and st.button(
            "Réinitialiser les résultats", use_container_width=True
        ):
            clear_dashboard_result()
            st.toast("Résultats réinitialisés.")
            st.rerun()


def _run_evaluation(config) -> None:
    with st.spinner("Évaluation du RAG en cours..."):
        try:
            result = run_evaluation(config)
            save_dashboard_result(result)
        except RagApiError as error:
            render_api_error(error, debug_enabled=True)
            return

    st.toast("Évaluation terminée.")


def _render_results(result: dict) -> None:
    st.caption("Dernière évaluation terminée.")
    render_summary_cards(result)

    retrieval_tab, answer_tab = st.tabs(["Recherche documentaire", "Réponse générée"])

    with retrieval_tab:
        st.subheader("Qualité du retrieval")
        st.caption(
            "Ces indicateurs évaluent si les bons extraits remontent au bon endroit."
        )
        render_retrieval_scores(result.get("average_retrieval", {}))

    with answer_tab:
        st.subheader("Qualité de la réponse")
        st.caption(
            "Ces indicateurs évaluent l'exactitude, la couverture et la pertinence."
        )
        render_answer_scores(result.get("average_answer_quality", {}))


current_user = require_authenticated_user()
apply_theme()

if not is_usage_admin(current_user):
    st.error("Cette page est réservée aux administrateurs.")
    st.stop()

evaluator_config = _load_evaluator_config_or_stop()
_render_sidebar()

render_page_header(
    "Dashboard RAG",
    "Lance une évaluation pour vérifier la qualité des sources récupérées et des réponses générées.",
)

if st.button("Lancer l'évaluation", type="primary", use_container_width=True):
    _run_evaluation(evaluator_config)

result = get_dashboard_result()
if result:
    _render_results(result)
else:
    render_dashboard_empty_state()
