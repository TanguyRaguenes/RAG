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
RAG_ORCHESTRATOR_TEST_CONNEXION_URL = os.getenv("RAG_ORCHESTRATOR_TEST_CONNEXION_URL")
RAG_ORCHESTRATOR_ASK_QUESTION_URL = os.getenv("RAG_ORCHESTRATOR_ASK_QUESTION_URL")
ROLE_ASSISTANT = "assistant"


def _ensure_env(name: str, value: str | None) -> None:
    if not value:
        st.error(f"Variable d'environnement manquante : {name}")
        st.stop()


_ensure_env("RAG_ORCHESTRATOR_TEST_CONNEXION_URL", RAG_ORCHESTRATOR_TEST_CONNEXION_URL)
_ensure_env("RAG_ORCHESTRATOR_ASK_QUESTION_URL", RAG_ORCHESTRATOR_ASK_QUESTION_URL)


def _build_chunk_header(i: int, path: str, chunk_index, similarity) -> str:
    header = f"Extrait {i} — {path}"
    if chunk_index is not None:
        header += f" (chunk {chunk_index})"
    if similarity is not None:
        header += f" — sim={similarity:.2f}"
    return header


def _render_chunks(retrieved_chunks: list[dict]) -> None:
    with st.expander("🔍 Extraits pertinents"):
        for i, chunk in enumerate(retrieved_chunks, start=1):
            meta = chunk.get("metadata", {})
            path = meta.get("path", "Source inconnue")
            chunk_index = meta.get("chunk_index")
            similarity = chunk.get("similarity")
            text_content = chunk.get("document", "Contenu vide")

            header = _build_chunk_header(i, path, chunk_index, similarity)
            with st.expander(header, expanded=(i == 1)):
                st.markdown(text_content)


# --- FONCTIONS UTILITAIRES ---
def afficher_message(
    role: str,
    llm_response: str,
    retrieved_documents: dict | None = None,
    retrieved_chunks: list[dict] | None = None,
    duration: str | None = None,
    model: str | None = None,
    total_tokens: int | None = None,
    cost: float | None = None,
    generated_prompt: list[dict] | None = None,
):
    """Affiche un message + métadonnées assistant."""
    with st.chat_message(role):
        st.markdown(llm_response)

        # ⬇️ early-return : supprime un gros niveau d'imbrication
        if role != ROLE_ASSISTANT:
            return

        # infos compactes
        infos = []
        if model:
            infos.append(f"🤖 {model}")
        if duration:
            infos.append(f"⏱️ {duration}")
        if total_tokens:
            infos.append(f"🪙 {total_tokens} tokens")
        if cost:
            infos.append(f"💰 {cost}€")
        if infos:
            st.caption(" — ".join(infos))

        if retrieved_documents:
            with st.expander("📚 Wikis consultés"):
                for title, count in retrieved_documents.items():
                    st.markdown(f"- `{title}` — **{count}** extrait(s)")

        if retrieved_chunks:
            _render_chunks(retrieved_chunks)

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

    # --- SÉLECTEUR DE LLM ---
    st.subheader("⚙️ Configuration")
    llm_type = st.radio(
        "Moteur d'intelligence :",
        ["Cloud (API)", "Local (Ollama)"],
        index=0,
        help="Choisissez entre l'exécution locale ou via l'API.",
    )

    st.divider()

    if st.button("🔍 État API", use_container_width=True):
        with st.status("Ping API...", expanded=False) as status:
            try:
                response = requests.get(
                    f"{RAG_ORCHESTRATOR_TEST_CONNEXION_URL}/docs", timeout=5
                )
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
        total_tokens=message.get("total_tokens"),
        model=message.get("model"),
        generated_prompt=message.get("generated_prompt"),
    )

# --- ZONE DE CHAT ---
if prompt := st.chat_input("Ex : C'est quoi les Microservices New Way ?"):
    user_msg = {"role": "user", "content": prompt}

    st.session_state.messages.append(user_msg)
    afficher_message("user", prompt)

    provider: str = ""

    if llm_type == "Cloud (API)":
        provider = "api"
    else:
        provider = "local"

    with st.spinner(f"IsiDore ({llm_type}) réfléchit..."):
        try:
            payload = {"question": prompt, "provider": provider}

            # Utilisation de l'URL dynamique choisie dans la barre latérale
            response = requests.post(
                RAG_ORCHESTRATOR_ASK_QUESTION_URL, json=payload, timeout=360
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
            total_tokens = full_response.get("total_tokens")
            cost = full_response.get("cost")
            generated_prompt = full_response.get("generated_prompt")
            duration = full_response.get("duration", "N/A")

            assistant_msg = {
                "role": ROLE_ASSISTANT,
                "content": llm_answer,
                "retrieved_documents": retrieved_documents,
                "retrieved_chunks": retrieved_chunks,
                "model": model,
                "total_tokens": total_tokens,
                "cost": cost,
                "generated_prompt": generated_prompt,
                "duration": duration,
            }
            st.session_state.messages.append(assistant_msg)

            afficher_message(
                ROLE_ASSISTANT,
                llm_answer,
                retrieved_documents=retrieved_documents,
                retrieved_chunks=retrieved_chunks,
                duration=duration,
                total_tokens=total_tokens,
                model=model,
                cost=cost,
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
