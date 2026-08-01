import math
from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class ScoreMetric:
    """Métrique optionnelle avec son échelle et son aide utilisateur."""

    label: str
    value: float | None
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
    """Affiche l'état vide du dashboard lorsqu'aucune évaluation n'a été lancée."""
    st.caption(
        "Aucun résultat pour le moment. Lance une évaluation pour mesurer le retrieval "
        "et la qualité des réponses."
    )


def render_summary_cards(result: dict) -> None:
    """Affiche les cartes de synthèse du résultat d'évaluation RAG.

    Args:
        result: Résultat d'évaluation ou de dashboard à stocker en session.
    """
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
            _scaled_score(answer.get(key), 5.0)
            for key in ("accuracy", "completeness", "relevance")
        ]
    )

    col1, col2, col3, col4 = st.columns(4)
    total_questions = result.get("total_questions")
    question_label = str(int(total_questions)) if total_questions is not None else "N/A"
    col1.metric("Questions", question_label)
    col2.metric("Durée", str(result.get("total_duration", "N/A")))
    col3.metric("Retrieval", _format_average(retrieval_average))
    col4.metric("Réponse", _format_average(answer_average))


def render_retrieval_scores(retrieval: dict) -> None:
    """Affiche les scores de retrieval dans le dashboard Streamlit.

    Args:
        retrieval: Scores de retrieval à afficher dans le dashboard d'évaluation.
    """
    metrics = [
        ScoreMetric("MRR", _as_float(retrieval.get("mrr")), 1.0, RETRIEVAL_HELP["MRR"]),
        ScoreMetric(
            "nDCG", _as_float(retrieval.get("ndcg")), 1.0, RETRIEVAL_HELP["nDCG"]
        ),
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
    """Affiche les scores de qualité de réponse dans le dashboard Streamlit.

    Args:
        answer: Scores de qualité de réponse à afficher dans le dashboard d'évaluation.
    """
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
    """Affiche une grille de scores homogène pour le dashboard.

    Args:
        metrics: Couples libellé/valeur affichés dans une grille de scores.
    """
    columns = st.columns(2)
    for index, metric in enumerate(metrics):
        with columns[index % 2]:
            value_label = _format_score(metric.value, metric.scale_max)
            st.markdown(f"**{metric.label}** · {value_label}")
            if metric.value is not None:
                st.progress(_clamp(metric.value / metric.scale_max))
            else:
                st.caption("Métrique non calculée.")
            st.caption(metric.help_text)


def _format_score(value: float | None, scale_max: float) -> str:
    """Formate un score en pourcentage ou sur son échelle absolue."""
    if value is None:
        return "N/A"
    if scale_max == 1.0:
        return f"{value:.0%}"
    return f"{value:.1f}/{int(scale_max)}"


def _average(values: list[float | None]) -> float | None:
    """Calcule la moyenne des valeurs disponibles sans inventer de zéro."""
    valid_values = [value for value in values if value is not None and value >= 0]
    if not valid_values:
        return None
    return sum(valid_values) / len(valid_values)


def _as_float(value: object) -> float | None:
    """Convertit une valeur en flottant ou indique qu'elle est absente."""
    try:
        parsed_value = float(value)
    except (TypeError, ValueError):
        return None
    return parsed_value if math.isfinite(parsed_value) else None


def _scaled_score(value: object, scale_max: float) -> float | None:
    """Normalise une métrique optionnelle sur une échelle donnée."""
    parsed_value = _as_float(value)
    return parsed_value / scale_max if parsed_value is not None else None


def _format_average(value: float | None) -> str:
    """Affiche une moyenne disponible ou une absence explicite."""
    return f"{value:.0%}" if value is not None else "N/A"


def _clamp(value: float) -> float:
    """Borne une valeur entre zéro et un."""
    return min(max(value, 0.0), 1.0)
