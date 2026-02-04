import math
import os

import altair as alt  # Nécessaire pour les camemberts
import pandas as pd
import requests
import streamlit as st

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Dashboard RAG", page_icon="📊", layout="wide")

# --- CSS ET STYLE ---
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

tooltips = {
    "MRR": "MRR (Mean Reciprocal Rank) : \n \n"
    "On regarde la position du tout premier chunk pertinent. Puis on calule l'inverse. \n"
    "rappel : L'inverse d'une fraction consiste à échanger le numérateur (le chiffre du haut) et le dénominateur (le chiffre du bas) \n"
    "tout en conservant le même signe. Mathématiquement, si nous avons une fraction 'a/b', son inverse est 'b/a'. \n \n"
    "Exemple : \n"
    "Si le bon chunk est en 1ère position : score = 1/1 = 1.0 \n"
    "Si le bon chunk est en 2ème position : score = 1/2 = 0.5 \n"
    "Si le bon chunk est en 10ème position : score = 1/10 = 0.1 \n"
    "Pas de chunk pertinent ? Score = 0.  \n \n",
    "nDCG": "nDCG (Normalized Discounted Cumulative Gain) : \n \n"
    "On vérifie si les meilleurs chunks sont bien placés tout en haut de la liste. \n"
    "On compare le score du classement du retriever avec le score d'un classement 'Idéal' (parfait). \n"
    "rappel : Le logarithme (log2) sert ici d'amortisseur. Contrairement à une division simple qui tue le score trop vite \n"
    "(diviser par 2 fait perdre 50%), le log réduit le score plus doucement à mesure qu'on descend dans la liste (pour plus de détails voir plus bas). \n"
    "C'est une 'punition' progressive pour les bons chunks mal classés. \n \n"
    "Exemple (Question : 'Différence Kelio/Moffi') : \n"
    "- Chunk A (Parfait) et Chunk B (Moyen) sont pertinents. Chunk C (Inutile) est du bruit. \n"
    "- Classement [A, B, C] (Idéal) : Le meilleur est en 1er -> Score = 1.0 (100%) \n"
    "- Classement [B, A, C] (Moyen) : Le meilleur est tombé en 2ème -> Score < 1.0 (ex: 0.85) \n"
    "- Classement [C, B, A] (Mauvais): Les bons chunks sont à la fin -> Score très faible. \n \n",
    "Recall": "Recall@K (Rappel - Couverture de Mots-clés) : \n \n"
    "On regarde si on a trouvé TOUS les mots-clés demandés par l'utilisateur. \n"
    "On divise le nombre de mots trouvés par le nombre total de mots-clés cherchés. \n"
    "rappel : Dans un contexte académique, le Rappel mesure le % de documents trouvés par rapport à la base totale. \n"
    "Ici, faute de connaitre la base par cœur, on utilise une approximation : 'ai-je trouvé tous les mots-clefs ?'. \n \n"
    "Exemple (Keywords cherchés : 'Kelio', 'Moffi', 'Badgeage') : \n"
    "- Si les chunks contiennent 'Kelio' et 'Moffi' mais pas 'Badgeage' : \n"
    "- Trouvés = 2. Total attendu = 3. \n"
    "- Score = 2/3 = 0.66 (66% de couverture). \n \n",
    "Precision": "# Precision@K (accuracy) : \n \n"
    "On regarde la 'pureté' de la liste des chunks: y a-t-il des déchets (chunks inutiles) parmi les chunks affichés ? \n"
    "On divise le nombre de chunks pertinents par le nombre de chunks affichés (K). \n"
    "rappel : L'ordre n'a aucune importance ici. Que le déchet soit en 1ère ou en 3ème position, \n"
    "il compte de la même façon comme une erreur de accuracy. \n \n"
    "Exemple (Question : 'Frais Cleemy', on affiche 3 chunks) : \n"
    "- Chunk 1 : Pertinent (Parle de Cleemy) \n"
    "- Chunk 2 : Bruit (Menu Cantine) \n"
    "- Chunk 3 : Pertinent (Parle de Frais) \n"
    "- Score : 2 pertinents sur 3 affichés = 2/3 = 0.66 (66%).",
    "accuracy": "accuracy : \n \n"
    "Exactitude factuelle de la réponse par rapport à la réponse de référence. \n"
    "Note de 1 à 5 : \n"
    "1 : incorrecte (toute réponse erronée doit recevoir 1) \n"
    "5 : idéale — parfaitement exacte \n"
    "Une réponse acceptable obtiendrait généralement 3. \n \n",
    "completeness": "completeness : \n \n"
    "Degré de completeness de la réponse, c’est-à-dire sa capacité à couvrir tous les aspects de la question. \n"
    "Note de 1 à 5 : \n"
    "1 : très insuffisante — informations clés manquantes \n"
    "5 : idéale — toutes les informations de la réponse de référence sont présentes \n"
    "N’attribuer 5 que si l’intégralité des informations attendues est fournie. \n \n",
    "relevance": "relevance : \n \n"
    "1 : très faible — hors sujet \n"
    "5 : idéale — répond directement à la question sans information superflue \n"
    "N’attribuer 5 que si la réponse est strictement pertinente et ne contient aucun ajout inutile. \n \n",
}


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
        .replace("\n", "&#10;")
    )


# --- FONCTION 1 : BARRE DE PROGRESSION LINEAIRE ---
def display_progress_metric(label, value, scale_max=1.0):
    progress = min(max(value / scale_max, 0.0), 1.0)
    st.markdown(
        f'<span title="Information sur la métrique {html_escape(tooltips[label])}"><b>{label}</b></span>',
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 3])
    with cols[0]:
        if math.isclose(scale_max, 1.0):
            st.write(f"### {value:.2%}")
        else:
            st.write(f"### {value:.1f}/{int(scale_max)}")
    with cols[1]:
        st.progress(progress)


# --- FONCTION 2 : CAMEMBERT (DONUT CHART) ---
def make_donut(input_response, input_text, input_color, scale_max=1.0):

    PERCENT_VALUE = "% value"

    if scale_max > 1.0:
        # Normalisation pour les notes sur 5 (ex: 4.2 devient 84%)
        pct = (input_response / scale_max) * 100
        display_val = f"{input_response:.1f}/{int(scale_max)}"
    else:
        # Pourcentage classique
        pct = input_response * 100
        display_val = f"{pct:.1f}%"

    # Données pour le graphique (La partie pleine vs la partie vide)
    source = pd.DataFrame({"Topic": ["", input_text], PERCENT_VALUE: [100 - pct, pct]})

    source_bg = pd.DataFrame({"Topic": ["", input_text], PERCENT_VALUE: [100, 0]})

    plot = (
        alt.Chart(source)
        .mark_arc(innerRadius=45, cornerRadius=25)
        .encode(
            theta=PERCENT_VALUE,
            color=alt.Color(
                "Topic",
                scale=alt.Scale(
                    domain=[input_text, ""],
                    # Couleur donnée vs Gris clair pour le vide
                    range=[input_color, "#e6e6e6"],
                ),
                legend=None,
            ),
        )
        .properties(width=130, height=130)
    )

    text = plot.mark_text(
        align="center",
        color=input_color,
        font="Lato",
        fontSize=20,
        fontWeight=700,
        fontStyle="italic",
    ).encode(text=alt.value(display_val))
    plot_bg = (
        alt.Chart(source_bg)
        .mark_arc(innerRadius=45, cornerRadius=20)
        .encode(
            theta=PERCENT_VALUE,
            color=alt.Color(
                "Topic",
                scale=alt.Scale(
                    domain=[input_text, ""], range=[input_color, "#e6e6e6"]
                ),
                legend=None,
            ),
        )
        .properties(width=130, height=130)
    )

    return plot_bg + plot + text


# --- VARIABLES D'ENVIRONNEMENT ---
RAG_EVALUATOR_TEST_CONNEXION_URL = os.getenv("RAG_EVALUATOR_TEST_CONNEXION_URL")
RAG_EVALUATOR_EVALUATE_RAG_URL = os.getenv("RAG_EVALUATOR_EVALUATE_RAG_URL")

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Dashboard")
    st.info("Ce tableau de bord évalue la qualité du RAG.")

    if st.button("🔍 État API", use_container_width=True):
        with st.status("Ping API...", expanded=False) as status:
            try:
                response = requests.get(
                    f"{RAG_EVALUATOR_TEST_CONNEXION_URL}/docs", timeout=5
                )
                if response.status_code == 200:
                    status.update(label="Connecté ✅", state="complete")
                else:
                    status.update(
                        label=f"Erreur API ({response.status_code})", state="error"
                    )
            except Exception:
                status.update(label="Serveur injoignable ❌", state="error")

# --- HEADER ---
st.title("Evaluation du RAG")
st.caption("Évaluez la qualité de la récupération et des réponses du RAG.")
st.divider()

# --- BOUTON D'ACTION ---
if st.button("🚀 Lancer l'évaluation", use_container_width=True, type="primary"):
    with st.spinner("Evaluation en cours..."):
        try:
            # 1. APPEL API
            resp = requests.post(RAG_EVALUATOR_EVALUATE_RAG_URL, timeout=300)
            resp.raise_for_status()
            data = resp.json()

            # 2. EXTRACTION DONNÉES
            retrieval = data["average_retrieval"]
            st.session_state.mrr = float(retrieval["mrr"])
            st.session_state.ndcg = float(retrieval["ndcg"])
            st.session_state.recall = float(retrieval["recall"])
            st.session_state.precision = float(retrieval["precision"])

            answer = data["average_answer_quality"]
            st.session_state.feedback = str(answer.get("feedback", "Pas de feedback"))
            st.session_state.accuracy = float(answer["accuracy"])
            st.session_state.completeness = float(answer["completeness"])
            st.session_state.relevance = float(answer["relevance"])

            st.session_state.total_questions = int(data.get("total_questions", 0))
            st.session_state.duration = str(data.get("total_duration", "00:00"))
            st.session_state.evaluation_done = True

        except Exception as e:
            st.session_state.evaluation_done = False
            st.error(f"Erreur : {e}")

# --- AFFICHAGE DES RÉSULTATS ---
if st.session_state.get("evaluation_done"):
    st.success(
        f"Évaluation terminée sur {st.session_state.total_questions} questions ({st.session_state.duration})",
        icon="✅",
    )

    tab1, tab2 = st.tabs(["🔍 Retrieval Evaluation", "💬 Answer Evaluation"])

    # --- ONGLET 1 : RETRIEVAL ---
    with tab1:
        st.subheader("Performance du retriever")

        # 1. Barres linéaires
        col1, col2 = st.columns(2, gap="large")
        with col1:
            st.caption("Classement")
            display_progress_metric("MRR", st.session_state.mrr)
            display_progress_metric("nDCG", st.session_state.ndcg)
        with col2:
            st.caption("Contenu")
            display_progress_metric("Recall", st.session_state.recall)
            display_progress_metric("Precision", st.session_state.precision)

        st.divider()
        st.subheader("Visualisation Graphique")

        # 2. Camemberts (Donuts)
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.markdown(
                f'<span title="{html_escape(tooltips["MRR"])}"><b>MRR</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(st.session_state.mrr, "MRR", "#29b5e8"),
                use_container_width=True,
            )
        with d2:
            st.markdown(
                f'<span title="{html_escape(tooltips["nDCG"])}"><b>nDCG</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(st.session_state.ndcg, "nDCG", "#117070"),
                use_container_width=True,
            )
        with d3:
            st.markdown(
                f'<span title="{html_escape(tooltips["Recall"])}"><b>Recall</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(st.session_state.recall, "Recall", "#FF6B6B"),
                use_container_width=True,
            )
        with d4:
            st.markdown(
                f'<span title="{html_escape(tooltips["Precision"])}"><b>Precision</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(st.session_state.precision, "Precision", "#FCA311"),
                use_container_width=True,
            )

        # 3. Histogramme Comparatif
        st.markdown("#### Comparaison Globale")
        chart_data = pd.DataFrame(
            {
                "Métrique": ["MRR", "nDCG", "Recall", "Precision"],
                "Score": [
                    st.session_state.mrr,
                    st.session_state.ndcg,
                    st.session_state.recall,
                    st.session_state.precision,
                ],
            }
        )
        st.bar_chart(chart_data, x="Métrique", y="Score", color="#29b5e8")

    # --- ONGLET 2 : GENERATION ---
    with tab2:
        st.subheader("Performance du LLM")

        # CORRECTION : st.columns(3) est bien là
        c1, c2, c3 = st.columns(3)
        with c1:
            display_progress_metric(
                "accuracy", st.session_state.accuracy, scale_max=5.0
            )
        with c2:
            display_progress_metric(
                "completeness", st.session_state.completeness, scale_max=5.0
            )
        with c3:
            display_progress_metric(
                "relevance", st.session_state.relevance, scale_max=5.0
            )

        st.divider()
        st.subheader("Visualisation Graphique (Note sur 5)")

        # Camemberts pour les notes sur 5
        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown(
                f'<span title="{html_escape(tooltips["accuracy"])}"><b>accuracy</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(
                    st.session_state.accuracy, "Accuracy", "#27AE60", scale_max=5.0
                ),
                use_container_width=True,
            )
        with g2:
            st.markdown(
                f'<span title="{html_escape(tooltips["completeness"])}"><b>completeness</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(
                    st.session_state.completeness,
                    "Completeness",
                    "#8E44AD",
                    scale_max=5.0,
                ),
                use_container_width=True,
            )
        with g3:
            st.markdown(
                f'<span title="{html_escape(tooltips["relevance"])}"><b>relevance</b></span>',
                unsafe_allow_html=True,
            )
            st.altair_chart(
                make_donut(
                    st.session_state.relevance, "Relevance", "#E67E22", scale_max=5.0
                ),
                use_container_width=True,
            )

        if "feedback" in st.session_state:
            st.info(f"💡 **Feedback Global** : {st.session_state.feedback}")
