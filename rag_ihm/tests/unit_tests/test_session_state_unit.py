from types import SimpleNamespace

from app.state import session_state


def test_chat_messages_are_initialized_appended_and_cleared(monkeypatch) -> None:
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_state, "st", fake_streamlit)

    assert session_state.get_chat_messages() == []

    session_state.append_chat_message({"role": "user", "content": "Bonjour"})

    assert session_state.get_chat_messages() == [{"role": "user", "content": "Bonjour"}]

    session_state.clear_chat_messages()

    assert session_state.get_chat_messages() == []


def test_pending_prompt_is_popped_once(monkeypatch) -> None:
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_state, "st", fake_streamlit)

    session_state.set_pending_prompt("question")

    assert session_state.pop_pending_prompt() == "question"
    assert session_state.pop_pending_prompt() is None


def test_dashboard_result_is_returned_only_when_it_is_a_dict(monkeypatch) -> None:
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_state, "st", fake_streamlit)

    session_state.save_dashboard_result({"score": 1})
    assert session_state.get_dashboard_result() == {"score": 1}

    fake_streamlit.session_state[session_state.DASHBOARD_RESULT_KEY] = "invalid"
    assert session_state.get_dashboard_result() is None

    session_state.clear_dashboard_result()
    assert session_state.DASHBOARD_RESULT_KEY not in fake_streamlit.session_state


def test_theme_preference_state_defaults_and_tracks_sync(monkeypatch) -> None:
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr(session_state, "st", fake_streamlit)

    assert session_state.get_theme_mode() == "Clair"
    assert not session_state.has_synced_theme_preference()

    session_state.set_theme_mode("Sombre")
    session_state.mark_theme_preference_synced("Sombre")

    assert session_state.get_theme_mode() == "Sombre"
    assert session_state.has_synced_theme_preference()
    assert session_state.get_persisted_theme_mode() == "Sombre"
