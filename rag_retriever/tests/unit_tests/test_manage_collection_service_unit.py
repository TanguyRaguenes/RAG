from app.services.manage_collection_service import delete_collection


class FakeVectorStoreRepository:
    def __init__(self) -> None:
        self.reset_collection_name = None

    def reset_collection(self, collection_name: str) -> None:
        self.reset_collection_name = collection_name


def test_delete_collection_recreates_configured_collection() -> None:
    repository = FakeVectorStoreRepository()

    delete_collection({"collection": {"name": "wiki_chunks"}}, repository)

    assert repository.reset_collection_name == "wiki_chunks"
