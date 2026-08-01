import pytest
from app.components.chat import EXAMPLE_QUESTIONS
from app.services import rag_api_client
from app.services.auth_service import (
    ACCESS_TOKEN_KEY,
    IDENTITY_VERIFIED_KEY,
    USER_KEY,
)
from streamlit.testing.v1 import AppTest


def test_examples_disappear_after_first_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RAG_ORCHESTRATOR_TEST_CONNEXION_URL", "http://rag.test")
    monkeypatch.setenv(
        "RAG_ORCHESTRATOR_ASK_QUESTION_URL", "http://rag.test/ask_question"
    )
    monkeypatch.setattr(
        rag_api_client,
        "ask_question",
        lambda *args: {
            "llm_response": "Réponse générée",
            "retrieved_documents": {},
            "retrieved_chunks": [],
            "generated_prompt": [],
        },
    )

    app = AppTest.from_file("app/main.py")
    app.session_state[ACCESS_TOKEN_KEY] = "token"
    app.session_state[USER_KEY] = {"issuer": "issuer", "sub": "user", "groups": []}
    app.session_state[IDENTITY_VERIFIED_KEY] = True
    app.run(timeout=20)

    assert set(EXAMPLE_QUESTIONS).issubset({button.label for button in app.button})

    app.chat_input[0].set_value("Première question").run(timeout=20)

    assert not set(EXAMPLE_QUESTIONS) & {button.label for button in app.button}
    assert any(markdown.value == "Réponse générée" for markdown in app.markdown)
    assert not app.exception
