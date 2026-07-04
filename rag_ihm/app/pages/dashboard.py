import streamlit as st

from app.components.common import (
    render_api_error,
    render_healthcheck_status,
    render_page_header,
)
from app.components.dashboard import (
    render_answer_scores,
    render_dashboard_empty_state,
    render_retrieval_scores,
    render_summary_cards,
)
from app.services.auth_service import require_authenticated_user
from app.services.rag_api_client import (
    RagApiError,
    check_api_health,
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


def _render_sidebar(evaluator_config) -> None:
    with st.sidebar:
        st.subheader("Évaluation")
        st.caption("Mesure la qualité du retrieval et des réponses générées.")
        st.divider()

        if st.button("🔍 État API", use_container_width=True):
            render_healthcheck_status(
                "Ping API...",
                lambda: check_api_health(evaluator_config.health_url),
            )

        has_result = get_dashboard_result() is not None
        if has_result and st.button("Réinitialiser les résultats", use_container_width=True):
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
        st.caption("Ces indicateurs évaluent si les bons extraits remontent au bon endroit.")
        render_retrieval_scores(result.get("average_retrieval", {}))

    with answer_tab:
        st.subheader("Qualité de la réponse")
        st.caption("Ces indicateurs évaluent l'exactitude, la couverture et la pertinence.")
        render_answer_scores(result.get("average_answer_quality", {}))


evaluator_config = _load_evaluator_config_or_stop()
require_authenticated_user()
apply_theme()
_render_sidebar(evaluator_config)

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
