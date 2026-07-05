from app.api.routers.query_router import _format_duration, _get_llm_provider


def test_format_duration_converts_milliseconds_to_mm_ss() -> None:
    assert _format_duration(0) == "00:00"
    assert _format_duration(61_500) == "01:01"


def test_get_llm_provider_reads_provider_config() -> None:
    config = {
        "llm": {
            "api": {"provider": "openai"},
            "local": {"provider": "ollama"},
        }
    }

    assert _get_llm_provider("api", config) == "openai"
    assert _get_llm_provider("local", config) == "ollama"
