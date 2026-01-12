from pydantic import BaseModel

from app.schemas.save_items_response_schema import SaveItemsResponseBase


class IngestBulkResponseBase(BaseModel):
    savedItems: SaveItemsResponseBase
    duration: str
