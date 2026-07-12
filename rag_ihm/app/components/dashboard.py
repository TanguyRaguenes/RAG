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
            normalized = _clamp(metric.value / metric.scale_max)
            value_label = _format_score(metric.value, metric.scale_max)
            st.markdown(f"**{metric.label}** · {value_label}")
            st.progress(normalized)
            st.caption(metric.help_text)


def _render_kpi(column, label: str, value: str) -> None:
    """Affiche un indicateur KPI avec son libellé et sa valeur.

    Args:
        column: Colonne Streamlit dans laquelle rendre le KPI.
        label: Libellé affiché à l'utilisateur pour le statut, le score ou le KPI.
        value: Valeur à convertir, borner ou formater.
    """
    with column:
        st.caption(label)
        st.markdown(f"### {value}")


def _format_score(value: float, scale_max: float) -> str:
    """Formate un score numérique en pourcentage lisible.

    Args:
        value: Valeur à convertir, borner ou formater.
        scale_max: Valeur maximale utilisée pour convertir un score en pourcentage.

    Returns:
        Score formaté en pourcentage lisible.
    """
    if scale_max == 1.0:
        return f"{value:.0%}"
    return f"{value:.1f}/{int(scale_max)}"


def _average(values: list[float]) -> float:
    """Calcule la moyenne de valeurs numériques disponibles.

    Args:
        values: Valeurs numériques utilisées pour un calcul agrégé.

    Returns:
        Moyenne des valeurs numériques disponibles.
    """
    valid_values = [value for value in values if value >= 0]
    if not valid_values:
        return 0.0
    return sum(valid_values) / len(valid_values)


def _as_float(value: object) -> float:
    """Convertit une valeur optionnelle en nombre flottant affichable.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Valeur convertie en float, ou `None` si la conversion échoue.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: float) -> float:
    """Borne une valeur numérique entre deux limites inclusives.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Valeur bornée entre les limites fournies.
    """
    return min(max(value, 0.0), 1.0)
