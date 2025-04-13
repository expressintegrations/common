from typing import Optional

from pydantic import BaseModel


class SimpleBoard(BaseModel):
    id: str
    name: str


class BoardColumn(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    settings_str: Optional[str] = None


class SubitemsSettings(BaseModel):
    allowMultipleItems: bool
    itemTypeName: str
    displayType: str
    boardIds: list[int]
