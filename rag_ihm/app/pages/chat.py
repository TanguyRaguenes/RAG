import os

import requests
import streamlit as st

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="IsiDore", page_icon="🤖", layout="centered")

# --- STYLES CSS ---
st.markdown(
    """
    <style>
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    .stButton>button { border-radius: 8px; }
    .stExpander { border: none; box-shadow: none; background-color: transparent; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- VARIABLES D'ENVIRONNEMENT ---
RAG_API_TEST_CONNEXION_URL = os.getenv("RAG_API_TEST_CONNEXION_URL")
RAG_API_ASK_QUESTION_URL = os.getenv("RAG_API_ASK_QUESTION_URL")

# --- FONCTIONS UTILITAIRES ---


def afficher_message(role, content, sources=None, chunks=None, duration=None):
    """Fonction pour afficher un message et ses métadonnées"""
    with st.chat_message(role):
        st.markdown(content)

        # Affichage des métadonnées (seulement pour l'assistant)
        if role == "assistant":
            if duration:
                st.caption(f"⏱️ Généré en : {duration}")

            if sources:
                with st.expander("📚 Wikis consultés"):
                    unique_sources = sorted(list(set(sources)))
                    for source in unique_sources:
                        st.markdown(f"- `{source}`")

            if chunks:
                with st.expander("🔍 Extraits pertinents"):
                    for i, chunk in enumerate(chunks):
                        path = chunk.get("metadata", {}).get("path", "Source inconnue")
                        text_content = chunk.get("document", "Contenu vide")
                        st.caption(f"**Extrait {i + 1}** — *{path}*")
                        st.info(text_content)


# --- BARRE LATÉRALE ---
with st.sidebar:
    image_path = "./assets/images/robot_isilog.png"
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
    else:
        st.title("🤖 IsiDore")  # Fallback si l'image manque

    st.caption("LLM basé sur la documentation interne ISILOG.")
    st.divider()

    # État du serveur
    if st.button("🔍 État API", use_container_width=True):
        with st.status("Ping API...", expanded=False) as status:
            try:
                response = requests.get(f"{RAG_API_TEST_CONNEXION_URL}/docs", timeout=5)
                if response.status_code == 200:
                    status.update(label="Connecté ✅", state="complete")
                else:
                    status.update(
                        label=f"Erreur API ({response.status_code})", state="error"
                    )
            except Exception:
                status.update(label="Serveur injoignable ❌", state="error")

    # Reset
    if st.button("🗑️ Effacer la discussion", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- HEADER ---
st.title("IsiDore")
st.caption("Interrogez le LLM sur la documentation interne ISILOG.")

# --- INITIALISATION DE L'HISTORIQUE ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- AFFICHAGE DE L'HISTORIQUE ---
# On réaffiche tout l'historique au rechargement de la page
for message in st.session_state.messages:
    afficher_message(
        role=message["role"],
        content=message["content"],
        sources=message.get("sources"),
        chunks=message.get("chunks"),
        duration=message.get("duration"),
    )

# --- ZONE DE CHAT ---
if prompt := st.chat_input("Ex : C'est quoi les Microservices New Way ?"):
    # 1. Sauvegarde et affichage immédiat de la question utilisateur
    user_msg = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)
    afficher_message("user", prompt)

    # 2. Traitement de la réponse
    with st.spinner("IsiDore réfléchit..."):
        try:
            payload = {"question": prompt}
            response = requests.post(
                RAG_API_ASK_QUESTION_URL, json=payload, timeout=180
            )

            if response.status_code == 200:
                full_response = response.json()

                # Extraction des données
                data = full_response.get("answer", {})
                llm_answer = data.get("llm_answer", "Pas de réponse générée.")
                sources = data.get("sources", [])
                chunks = data.get(
                    "chunks", []
                )  # Note: vérifiez si votre API renvoie "chunks" ou "chunks"
                duration = full_response.get("duration", "N/A")

                # Sauvegarde complète dans le state (Texte + Métadonnées)
                assistant_msg = {
                    "role": "assistant",
                    "content": llm_answer,
                    "sources": sources,
                    "chunks": chunks,
                    "duration": duration,
                }
                st.session_state.messages.append(assistant_msg)

                # Affichage de la réponse
                afficher_message("assistant", llm_answer, sources, chunks, duration)

            else:
                st.error(f"Erreur API : {response.status_code}")

        except requests.exceptions.Timeout:
            st.error("⏳ Le serveur met trop de temps à répondre.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Impossible de contacter le serveur.")
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
