import streamlit as st
import requests
import os

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="IsiAssistant", 
    page_icon="🤖", 
    layout="centered"
    
)

# CSS pour un design moderne (bulles de chat et boutons)
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stButton>button { border-radius: 8px; }
    /* Style pour rendre les infos plus discrètes dans les expanders */
    .stExpander { border: none; box-shadow: none; background-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES D'ENVIRONNEMENT ---
# "http://api:8000" correspond au nom du service dans ton docker-compose
API_URL = os.getenv("API_URL", "http://api:8000")

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4712/4712035.png", width=100)
    st.title("IsiAssistant")
    st.info("LLM basé sur la documentation interne ISILOG.")
    
    st.divider()
    
    # Bouton de vérification de l'état du Backend
    if st.button("🔍 État du serveur", use_container_width=True):
        with st.status("Vérification...", expanded=False) as status:
            try:
                response = requests.get(f"{API_URL}/docs", timeout=5)
                if response.status_code == 200:
                    status.update(label="Connecté au Backend ✅", state="complete")
                else:
                    status.update(label=f"Erreur API ({response.status_code})", state="error")
            except Exception as e:
                status.update(label="Serveur injoignable ❌", state="error")

    # Bouton pour réinitialiser la conversation
    if st.button("🗑️ Effacer la discussion", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- TITRE PRINCIPAL ---
st.title("IsiAssistant")
st.caption("Interrogez le LLM sur la documentation interne ISILOG")

# --- GESTION DE L'HISTORIQUE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages stockés dans la session
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- ZONE D'INTERACTION ---
if prompt := st.chat_input("Ex: Liste moi les équipes chez ISILOG ?"):
    
    # 1. Affichage du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Réponse de l'Assistant
    with st.chat_message("assistant"):
        with st.spinner("Analyse du Wiki en cours..."):
            try:
                # Préparation de l'envoi au backend
                payload = {"question": prompt}
                # Timeout long (180s) pour laisser le temps au LLM local (Ollama) de générer
                response = requests.post(f"{API_URL}/ask_question", json=payload, timeout=180)
                
                if response.status_code == 200:
                    # Extraction des données selon ta structure Pydantic imbriquée
                    full_response = response.json()
                    
                    # On accède à l'objet 'answer' qui contient le coeur de la réponse
                    data = full_response.get("answer", {})
                    duration = full_response.get("duration", "N/A")
                    
                    llm_answer = data.get("llm_answer", "Désolé, je n'ai pas pu formuler de réponse.")
                    sources = data.get("sources", [])
                    chunks = data.get("chuncks", []) # Note: orthographe 'chuncks' du backend conservée

                    # A. Affichage du texte généré par l'IA
                    st.markdown(llm_answer)
                    
                    # B. Affichage du temps de génération
                    st.caption(f"⏱️ Généré en : {duration}")
                    
                    # C. Expander 1 : Liste des sources (Fichiers)
                    if sources:
                        with st.expander("📚 Sources (Fichiers consultés)"):
                            unique_sources = sorted(list(set(sources)))
                            for source in unique_sources:
                                st.markdown(f"- `{source}`")

                    # D. Expander 2 : Extraits textuels (Chunks)
                    if chunks:
                        with st.expander("📄 Extraits pertinents du Wiki"):
                            for i, chunk in enumerate(chunks):
                                path = chunk.get('metadata', {}).get('path', 'Source inconnue')
                                content = chunk.get('document', 'Contenu vide')
                                st.caption(f"Extrait {i+1} — Provenance : {path}")
                                st.info(content)

                    # E. Enregistrement de la réponse dans l'historique
                    st.session_state.messages.append({"role": "assistant", "content": llm_answer})
                
                else:
                    st.error(f"Le serveur a répondu avec une erreur ({response.status_code}).")
                    
            except requests.exceptions.Timeout:
                st.error("⏳ Timeout : Le LLM met trop de temps à répondre. Vérifiez la charge du serveur.")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Erreur de connexion : Impossible de joindre le backend.")
            except Exception as e:
                st.error(f"Une erreur inattendue est survenue : {e}")