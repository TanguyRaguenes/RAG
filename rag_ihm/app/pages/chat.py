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


def _ensure_env(name: str, value: str | None) -> None:
    if not value:
        st.error(f"Variable d'environnement manquante : {name}")
        st.stop()


_ensure_env("RAG_API_TEST_CONNEXION_URL", RAG_API_TEST_CONNEXION_URL)
_ensure_env("RAG_API_ASK_QUESTION_URL", RAG_API_ASK_QUESTION_URL)


# --- FONCTIONS UTILITAIRES ---
def afficher_message(
    role: str,
    llm_response: str,
    retrieved_documents: list[str] | None = None,
    retrieved_chunks: list[dict] | None = None,
    duration: str | None = None,
    model: str | None = None,
    generated_prompt: list[dict] | None = None,
):
    """Affiche un message + métadonnées assistant."""
    with st.chat_message(role):
        st.markdown(llm_response)

        if role == "assistant":
            # infos compactes
            infos = []
            if model:
                infos.append(f"🤖 {model}")
            if duration:
                infos.append(f"⏱️ {duration}")
            if infos:
                st.caption(" — ".join(infos))

            if retrieved_documents:
                with st.expander("📚 Wikis consultés"):
                    for document in sorted(set(retrieved_documents)):
                        st.markdown(f"- `{document}`")

            if retrieved_chunks:
                with st.expander("🔍 Extraits pertinents"):
                    for i, chunk in enumerate(retrieved_chunks, start=1):
                        path = chunk.get("metadata", {}).get("path", "Source inconnue")
                        text_content = chunk.get("document", "Contenu vide")
                        similarity = chunk.get("similarity")
                        if similarity is not None:
                            st.caption(
                                f"**Extrait {i}** — *{path}* — "
                                f"Similarité : **{similarity:.2f}**"
                            )
                        else:
                            st.caption(f"**Extrait {i}** — *{path}*")
                            st.info(text_content)

            if generated_prompt:
                with st.expander("🧩 Prompt généré"):
                    st.json(generated_prompt)


# --- BARRE LATÉRALE ---
with st.sidebar:
    image_path = "./assets/images/robot_isilog.png"
    if os.path.exists(image_path):
        st.image(image_path, use_container_width=True)
    else:
        st.title("🤖 IsiDore")

    st.caption("LLM basé sur la documentation interne ISILOG.")
    st.divider()

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
for message in st.session_state.messages:
    afficher_message(
        role=message["role"],
        llm_response=message["content"],
        retrieved_documents=message.get("retrieved_documents"),
        retrieved_chunks=message.get("retrieved_chunks"),
        duration=message.get("duration"),
        model=message.get("model"),
        generated_prompt=message.get("generated_prompt"),
    )

# --- ZONE DE CHAT ---
if prompt := st.chat_input("Ex : C'est quoi les Microservices New Way ?"):
    user_msg = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_msg)
    afficher_message("user", prompt)

    with st.spinner("IsiDore réfléchit..."):
        try:
            payload = {"question": prompt}
            response = requests.post(
                RAG_API_ASK_QUESTION_URL, json=payload, timeout=180
            )

            if response.status_code != 200:
                st.error(f"Erreur API : {response.status_code}")
                st.stop()

            # ✅ Aligné avec AskQuestionResponseBase
            full_response = response.json()

            llm_answer = full_response.get("llm_response", "Pas de réponse générée.")
            retrieved_documents = full_response.get("retrieved_documents", [])
            retrieved_chunks = full_response.get("retrieved_chunks", [])
            model = full_response.get("model")
            generated_prompt = full_response.get("generated_prompt")
            duration = full_response.get("duration", "N/A")

            assistant_msg = {
                "role": "assistant",
                "content": llm_answer,
                "retrieved_documents": retrieved_documents,
                "retrieved_chunks": retrieved_chunks,
                "model": model,
                "generated_prompt": generated_prompt,
                "duration": duration,
            }
            st.session_state.messages.append(assistant_msg)

            afficher_message(
                "assistant",
                llm_answer,
                retrieved_documents=retrieved_documents,
                retrieved_chunks=retrieved_chunks,
                duration=duration,
                model=model,
                generated_prompt=generated_prompt,
            )

        except requests.exceptions.Timeout:
            st.error("⏳ Le serveur met trop de temps à répondre.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Impossible de contacter le serveur.")
        except ValueError:
            st.error("Réponse API invalide (JSON non parsable).")
        except Exception as e:
            st.error(f"Une erreur est survenue : {e}")
