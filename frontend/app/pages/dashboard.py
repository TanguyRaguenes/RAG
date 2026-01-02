import streamlit as st
import pandas as pd
import time
import numpy as np

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

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Dashboard")
    st.info("Ce tableau de bord évalue la qualité du système RAG (Retrieval Augmented Generation).")
    # if st.button("⬅️ Retour au Chat"):
    #     st.switch_page("main.py")

# --- HEADER ---
st.title("Evaluation du RAG")
st.caption("Évaluez la qualité de la récupération et des réponses du système.")

st.divider()

# --- SECTION 1 : RETRIEVAL EVALUATION ---
st.header("🔍 Retrieval Evaluation")

# Bouton d'action (Pleine largeur)
if st.button("🚀 Lancer l'évaluation (Run Evaluation)", use_container_width=True, type="primary"):
    
    with st.spinner("Analyse des métriques en cours... (Simulation)"):
        time.sleep(1.5) # Simulation du temps de calcul
        
        # Génération de données aléatoires pour l'exemple
        st.session_state.mrr = 0.7298
        st.session_state.ndcg = 0.7387
        st.session_state.coverage = 83.8
        
        # Données pour le graphique
        categories = ['direct_fact', 'temporal', 'comparative', 'numerical', 'relationship', 'spanning', 'holistic']
        scores = np.random.uniform(0.5, 0.9, len(categories))
        st.session_state.df_chart = pd.DataFrame({"Category": categories, "Average MRR": scores})
        
        st.session_state.evaluation_done = True

# --- AFFICHAGE DES RÉSULTATS ---
if "evaluation_done" in st.session_state and st.session_state.evaluation_done:
    
    # Barre de succès verte comme sur l'image
    st.success("✅ Evaluation Complete: 150 tests performed", icon="✅")

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