import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide" # Important : layout large pour le tableau de bord
)

# --- CSS POUR LE STYLE "CARTE" ---
st.markdown("""
    <style>
    /* Style pour les cartes de métriques */
    div[data-testid="stMetric"] {
        background-color: #2b303b;
        border-left: 5px solid #ff4b4b; /* Bordure rouge comme sur l'image */
        padding: 15px;
        border-radius: 5px;
        color: white;
    }
    /* La 3ème carte en jaune */
    div[data-testid="column"] > div:nth-of-type(3) div[data-testid="stMetric"] {
        border-left: 5px solid #fca311; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES D'ENVIRONNEMENT ---
EVALUATOR_URL = os.getenv("EVALUATOR_URL")

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Dashboard")
    st.info("Ce tableau de bord évalue la qualité du système RAG (Retrieval Augmented Generation).")
    # if st.button("⬅️ Retour au Chat"):
    #     st.switch_page("main.py")
            # État du serveur
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

# --- SECTION 1 : RETRIEVAL EVALUATION ---
st.header("🔍 Retrieval Evaluation")

# Bouton d'action (Pleine largeur)
if st.button("🚀 Lancer l'évaluation (Run Evaluation)", use_container_width=True, type="primary"):
    
    with st.spinner("Analyse des métriques en cours... (Simulation)"):
        try:
            if not EVALUATOR_URL:
                raise RuntimeError("EVALUATOR_URL non défini")

            # appel evaluator (adapter la route si besoin)
            resp = requests.post(f"{EVALUATOR_URL}/evaluate_rag", timeout=100000)
            resp.raise_for_status()
            data = resp.json()

            # mapping GlobalEvaluatorResponse
            avg_r = data["average_retrieval"]

            st.session_state.mrr = float(avg_r["mrr"])
            st.session_state.ndcg = float(avg_r["ndcg"])
            st.session_state.coverage = float(avg_r["keyword_coverage"])

            # ton evaluator renvoie une moyenne globale => chart minimal
            st.session_state.df_chart = pd.DataFrame({
                "Category": ["global"],
                "Average MRR": [st.session_state.mrr],
            })

            st.session_state.total_questions = int(data["total_questions"])
            st.session_state.duration = str(data["total_duration"])

            st.session_state.evaluation_done = True

        except requests.Timeout:
            st.session_state.evaluation_done = False
            st.error("Timeout: l'évaluation a dépassé 300s.")
        except requests.HTTPError as e:
            st.session_state.evaluation_done = False
            st.error(f"Erreur API evaluator: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            st.session_state.evaluation_done = False
            st.error(f"Erreur evaluator: {e}")


# --- AFFICHAGE DES RÉSULTATS ---
if "evaluation_done" in st.session_state and st.session_state.evaluation_done:
    
    # Barre de succès verte comme sur l'image
    st.success(
        f"✅ Evaluation Complete: {st.session_state.get('total_questions','?')} tests performed "
        f"(duration: {st.session_state.get('duration','??:??')})",
        icon="✅"
    )

    # Création de deux colonnes : Métriques (Gauche) vs Graphique (Droite)
    col_metrics, col_chart = st.columns([1, 2], gap="large")

    with col_metrics:
        # Métrique 1 : MRR
        st.metric(
            label="Mean Reciprocal Rank (MRR)",
            value=f"{st.session_state.mrr:.4f}",
            delta="0.0124"
        )
        
        # Métrique 2 : nDCG
        st.metric(
            label="Normalized DCG (nDCG)",
            value=f"{st.session_state.ndcg:.4f}",
            delta="-0.0021",
            delta_color="inverse"
        )
        
        # Métrique 3 : Keyword Coverage
        st.metric(
            label="Keyword Coverage",
            value=f"{st.session_state.coverage}%",
            delta="1.2%"
        )

    with col_chart:
        st.subheader("Average MRR by Category")
        # Affichage du graphique à barres
        st.bar_chart(
            st.session_state.df_chart.set_index("Category"),
            color="#4A90E2", # Bleu Isilog
            height=320
        )

# --- SECTION 2 : ANSWER EVALUATION (Placeholder) ---
st.divider()
st.header("💬 Answer Evaluation")
st.info("Cette section sera implémentée ultérieurement avec les métriques de fidélité et de pertinence.")