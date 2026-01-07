import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import altair as alt # Nécessaire pour les camemberts

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard RAG",
    page_icon="📊",
    layout="wide"
)

# --- CSS ET STYLE ---
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTION 1 : BARRE DE PROGRESSION LINEAIRE ---
def display_progress_metric(label, value, scale_max=1.0):
    progress = min(max(value / scale_max, 0.0), 1.0)
    st.markdown(f"**{label}**")
    cols = st.columns([1, 3])
    with cols[0]:
        if scale_max == 1.0:
            st.write(f"### {value:.2%}")
        else:
            st.write(f"### {value:.1f}/{int(scale_max)}")
    with cols[1]:
        st.progress(progress)

# --- FONCTION 2 : CAMEMBERT (DONUT CHART) ---
def make_donut(input_response, input_text, input_color, scale_max=1.0):
    if scale_max > 1.0:
        # Normalisation pour les notes sur 5 (ex: 4.2 devient 84%)
        pct = (input_response / scale_max) * 100
        display_val = f"{input_response:.1f}/{int(scale_max)}"
    else:
        # Pourcentage classique
        pct = input_response * 100
        display_val = f"{pct:.1f}%"

    # Données pour le graphique (La partie pleine vs la partie vide)
    source = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100-pct, pct]
    })
    
    source_bg = pd.DataFrame({
        "Topic": ['', input_text],
        "% value": [100, 0]
    })
    
    plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
        theta="% value",
        color= alt.Color("Topic", scale=alt.Scale(
            domain=[input_text, ''],
            # Couleur donnée vs Gris clair pour le vide
            range=[input_color, '#e6e6e6']),
            legend=None),
    ).properties(width=130, height=130)
    
    text = plot.mark_text(align='center', color=input_color, font="Lato", fontSize=20, fontWeight=700, fontStyle="italic").encode(text=alt.value(display_val))
    plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
        theta="% value",
        color= alt.Color("Topic", scale=alt.Scale(
            domain=[input_text, ''],
            range=[input_color, '#e6e6e6']),
            legend=None),
    ).properties(width=130, height=130)
    
    return plot_bg + plot + text

# --- VARIABLES D'ENVIRONNEMENT ---
EVALUATOR_URL = os.getenv("EVALUATOR_URL", "http://localhost:8000")

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Dashboard")
    st.info("Ce tableau de bord évalue la qualité du système RAG.")
    
    if st.button("🔍 État API", use_container_width=True):
        with st.status("Ping API...", expanded=False) as status:
            try:
                response = requests.get(f"{EVALUATOR_URL}/docs", timeout=5)
                if response.status_code == 200:
                    status.update(label="Backend Connecté ✅", state="complete")
                else:
                    status.update(label=f"Erreur API ({response.status_code})", state="error")
            except Exception:
                status.update(label="Serveur injoignable ❌", state="error")

# --- HEADER ---
st.title("Evaluation du RAG")
st.caption("Évaluez la qualité de la récupération et des réponses du système.")
st.divider()

# --- BOUTON D'ACTION ---
if st.button("🚀 Lancer l'évaluation (Run Evaluation)", use_container_width=True, type="primary"):
    
    with st.spinner("Appel de l'API et calcul des métriques en cours..."):
        try:
            if not EVALUATOR_URL:
                raise RuntimeError("EVALUATOR_URL non défini")

            # 1. APPEL API
            resp = requests.post(f"{EVALUATOR_URL}/evaluate_rag", timeout=300)
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
    
    st.success(f"Évaluation terminée sur {st.session_state.total_questions} questions ({st.session_state.duration})", icon="✅")

    tab1, tab2 = st.tabs(["🔍 Retrieval Evaluation", "💬 Answer Evaluation"])

    # --- ONGLET 1 : RETRIEVAL ---
    with tab1:
        st.subheader("Performance du Moteur de Recherche")
        
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
            st.write("**MRR**")
            st.altair_chart(make_donut(st.session_state.mrr, "MRR", "#29b5e8"), use_container_width=True)
        with d2:
            st.write("**nDCG**")
            st.altair_chart(make_donut(st.session_state.ndcg, "nDCG", "#117070"), use_container_width=True)
        with d3:
            st.write("**Recall**")
            st.altair_chart(make_donut(st.session_state.recall, "Recall", "#FF6B6B"), use_container_width=True)
        with d4:
            st.write("**Precision**")
            st.altair_chart(make_donut(st.session_state.precision, "Precision", "#FCA311"), use_container_width=True)

        # 3. Histogramme Comparatif
        st.markdown("#### Comparaison Globale")
        chart_data = pd.DataFrame({
            "Métrique": ["MRR", "nDCG", "Recall", "Precision"],
            "Score": [st.session_state.mrr, st.session_state.ndcg, st.session_state.recall, st.session_state.precision]
        })
        st.bar_chart(chart_data, x="Métrique", y="Score", color="#29b5e8")


    # --- ONGLET 2 : GENERATION ---
    with tab2:
        st.subheader("Performance du LLM (Juge IA)")
        
        # CORRECTION : st.columns(3) est bien là
        c1, c2, c3 = st.columns(3)
        with c1:
            display_progress_metric("Précision", st.session_state.accuracy, scale_max=5.0)
        with c2:
            display_progress_metric("Complétude", st.session_state.completeness, scale_max=5.0)
        with c3:
            display_progress_metric("Pertinence", st.session_state.relevance, scale_max=5.0)

        st.divider()
        st.subheader("Visualisation Graphique (Note sur 5)")
        
        # Camemberts pour les notes sur 5
        g1, g2, g3 = st.columns(3)
        with g1:
            st.altair_chart(make_donut(st.session_state.accuracy, "Accuracy", "#27AE60", scale_max=5.0), use_container_width=True)
        with g2:
            st.altair_chart(make_donut(st.session_state.completeness, "Completeness", "#8E44AD", scale_max=5.0), use_container_width=True)
        with g3:
            st.altair_chart(make_donut(st.session_state.relevance, "Relevance", "#E67E22", scale_max=5.0), use_container_width=True)

        if "feedback" in st.session_state:
            st.info(f"💡 **Feedback Global** : {st.session_state.feedback}")