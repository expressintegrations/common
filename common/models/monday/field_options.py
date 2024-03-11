from typing import Optional, List

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


class OptionsRequest(BaseModel):
    board_id: Optional[int] = None
    automation_id: int
    dependency_data: Optional[dict] = None
    recipe_id: int
    integration_id: int
    page_request_data: Optional[Page] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class Payload(BaseModel):
    payload: OptionsRequest
