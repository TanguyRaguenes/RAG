from types import SimpleNamespace

from app.api.dependencies import get_config, get_vector_store_repository, get_wikis_collection


def test_dependencies_read_values_from_app_state() -> None:
    collection = object()

    class Repository:
        def __init__(self):
            self.names = []

        def get_or_create_collection(self, name: str):
            self.names.append(name)
            return collection

    repository = Repository()
    config = {"collection": {"name": "wiki_chunks"}}
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(config=config, vector_store_repository=repository)))

    assert get_config(request) is config
    assert get_vector_store_repository(request) is repository
    assert get_wikis_collection(request) is collection
    assert repository.names == ["wiki_chunks"]
