from types import SimpleNamespace

from app.api.dependencies import (
    get_config,
    get_vector_store_repository,
)


def test_dependencies_read_values_from_app_state() -> None:
    repository = object()
    config = {"collection": {"name": "wiki_chunks"}}
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(config=config, vector_store_repository=repository)
        )
    )

    assert get_config(request) is config
    assert get_vector_store_repository(request) is repository
