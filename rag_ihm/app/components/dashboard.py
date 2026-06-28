from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class ScoreMetric:
    label: str
    value: float
    scale_max: float
    help_text: str


RETRIEVAL_HELP = {
    "MRR": "Mesure si le premier extrait pertinent arrive tôt dans les résultats.",
    "nDCG": "Mesure si les meilleurs extraits sont bien classés.",
    "Recall": "Mesure si les informations attendues ont été retrouvées.",
    "Precision": "Mesure la proportion d'extraits utiles parmi ceux retournés.",
}

ANSWER_HELP = {
    "Accuracy": "Mesure l'exactitude factuelle de la réponse.",
    "Completeness": "Mesure si la réponse couvre les informations attendues.",
    "Relevance": "Mesure si la réponse répond directement à la question.",
}


def render_dashboard_empty_state() -> None:
    st.caption(
        "Aucun résultat pour le moment. Lance une évaluation pour mesurer le retrieval "
        "et la qualité des réponses."
    )


def render_summary_cards(result: dict) -> None:
    retrieval = result.get("average_retrieval", {})
    answer = result.get("average_answer_quality", {})

    retrieval_average = _average(
        [
            _as_float(retrieval.get("mrr")),
            _as_float(retrieval.get("ndcg")),
            _as_float(retrieval.get("recall")),
            _as_float(retrieval.get("precision")),
        ]
    )
    answer_average = _average(
        [
            _as_float(answer.get("accuracy")) / 5,
            _as_float(answer.get("completeness")) / 5,
            _as_float(answer.get("relevance")) / 5,
        ]
    )

    col1, col2, col3, col4 = st.columns(4)
    _render_kpi(col1, "Questions", str(int(result.get("total_questions", 0))))
    _render_kpi(col2, "Durée", str(result.get("total_duration", "N/A")))
    _render_kpi(col3, "Retrieval", f"{retrieval_average:.0%}")
    _render_kpi(col4, "Réponse", f"{answer_average:.0%}")


def render_retrieval_scores(retrieval: dict) -> None:
    metrics = [
        ScoreMetric("MRR", _as_float(retrieval.get("mrr")), 1.0, RETRIEVAL_HELP["MRR"]),
        ScoreMetric("nDCG", _as_float(retrieval.get("ndcg")), 1.0, RETRIEVAL_HELP["nDCG"]),
        ScoreMetric(
            "Recall",
            _as_float(retrieval.get("recall")),
            1.0,
            RETRIEVAL_HELP["Recall"],
        ),
        ScoreMetric(
            "Precision",
            _as_float(retrieval.get("precision")),
            1.0,
            RETRIEVAL_HELP["Precision"],
        ),
    ]
    _render_score_grid(metrics)


def render_answer_scores(answer: dict) -> None:
    metrics = [
        ScoreMetric(
            "Accuracy",
            _as_float(answer.get("accuracy")),
            5.0,
            ANSWER_HELP["Accuracy"],
        ),
        ScoreMetric(
            "Completeness",
            _as_float(answer.get("completeness")),
            5.0,
            ANSWER_HELP["Completeness"],
        ),
        ScoreMetric(
            "Relevance",
            _as_float(answer.get("relevance")),
            5.0,
            ANSWER_HELP["Relevance"],
        ),
    ]
    _render_score_grid(metrics)

    feedback = answer.get("feedback")
    if feedback:
        st.markdown(f"> {feedback}")


def _render_score_grid(metrics: list[ScoreMetric]) -> None:
    columns = st.columns(2)
    for index, metric in enumerate(metrics):
        with columns[index % 2]:
            normalized = _clamp(metric.value / metric.scale_max)
            value_label = _format_score(metric.value, metric.scale_max)
            st.markdown(f"**{metric.label}** · {value_label}")
            st.progress(normalized)
            st.caption(metric.help_text)


def _render_kpi(column, label: str, value: str) -> None:
    with column:
        st.caption(label)
        st.markdown(f"### {value}")


def _format_score(value: float, scale_max: float) -> str:
    if scale_max == 1.0:
        return f"{value:.0%}"
    return f"{value:.1f}/{int(scale_max)}"


def _average(values: list[float]) -> float:
    valid_values = [value for value in values if value >= 0]
    if not valid_values:
        return 0.0
    return sum(valid_values) / len(valid_values)


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)
