from typing import Optional, List, Any

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class FieldOption(BaseModel):
    title: str
    value: str


class Page(BaseModel):
    page: int


class OptionsResponse(BaseModel):
    options: List[FieldOption]
    is_paginated: Optional[bool] = None
    next_page_request_data: Optional[Page] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class Reference(BaseModel):
    title: str
    value: Any
    invalid: bool


class Dependencies(BaseModel):
    field_type_id: Optional[int] = None
    table: Optional[Reference] = None


class OptionsRequest(BaseModel):
    board_id: Optional[int] = None
    table: Optional[Reference] = None
    side: Optional[str] = None
    automation_id: Optional[int] = None
    dependency_data: Optional[Dependencies] = None
    recipe_id: Optional[int] = None
    integration_id: Optional[int] = None
    page_request_data: Optional[Page] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class Payload(BaseModel):
    payload: Optional[OptionsRequest] = None
