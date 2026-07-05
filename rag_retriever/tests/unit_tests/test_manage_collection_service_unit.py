from app.services.manage_collection_service import delete_collection


class FakeVectorStoreRepository:
    def __init__(self):
        self.deleted_collection = None
        self.created_collection = None

    def delete_collection_by_name(self, collection_name: str) -> None:
        self.deleted_collection = collection_name

    def get_or_create_collection(self, collection_name: str) -> None:
        self.created_collection = collection_name


def test_delete_collection_recreates_configured_collection() -> None:
    repository = FakeVectorStoreRepository()

    delete_collection({"collection": {"name": "wiki_chunks"}}, repository)

    assert repository.deleted_collection == "wiki_chunks"
    assert repository.created_collection == "wiki_chunks"
