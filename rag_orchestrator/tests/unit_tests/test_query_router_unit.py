from app.core.orchestration_observability import format_duration, get_llm_provider


def test_format_duration_converts_milliseconds_to_mm_ss() -> None:
    assert format_duration(0) == "00:00"
    assert format_duration(61_500) == "01:01"


def test_get_llm_provider_reads_provider_config() -> None:
    config = {
        "llm": {
            "api": {"provider": "openai"},
            "local": {"provider": "ollama"},
        }
    }

    assert get_llm_provider("api", config) == "openai"
    assert get_llm_provider("local", config) == "ollama"
