from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class SimpleBoard(BaseModel):
    id: str
    name: str


class BoardColumn(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    settings_str: Optional[str] = None


class SubitemsSettings(BaseModel):
    allow_multiple_items: bool
    item_type_name: str
    display_type: str
    board_ids: list[int]

    class Config:
        populate_by_name = True
        alias_generator = to_camel
