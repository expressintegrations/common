from typing import Optional, Any, List

from pydantic import BaseModel


class ColumnDetails(BaseModel):
    title: str
    settings_str: Optional[str] = None


class LinkedItem(BaseModel):
    id: str


class MirroredItem(BaseModel):
    linked_item: LinkedItem


class PersonOrTeam(BaseModel):
    id: str
    kind: str


class Country(BaseModel):
    name: str


class ColumnValue(BaseModel):
    id: str
    column: ColumnDetails
    type: str
    value: Optional[Any] = None
    text: Optional[str] = None

    # For column types "formula", "mirror", "board_relation"
    display_value: Optional[str] = None

    # For column type "mirror"
    # Settings string example: "{\"relation_column\":{\"subitems\":true},\"displayed_column\":{},\"displayed_linked_columns\":{\"4154746971\":[\"numeric_mkpy9ap3\"]},\"function\":\"sum\"}"
    mirrored_items: Optional[List[MirroredItem]] = None

    # For column type "people"
    persons_and_teams: Optional[List[PersonOrTeam]] = None

    # For column type "date"
    date: Optional[str] = None
    time: Optional[str] = None

    # For column type "checkbox"
    checked: Optional[bool] = None

    # For column type "board_relation"
    linked_item_ids: Optional[List[str]] = None

    # For column type "country"
    country: Optional[Country] = None

    # For column type "address"
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None

    # For column type "progress"
    # Setting string example: "{\"related_columns\":{\"isNormalized\":false,\"columns\":{\"status\":{\"isSelected\":true,\"percentage\":100}}}}"
