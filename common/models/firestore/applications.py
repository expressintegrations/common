from typing import Optional, List, Any

from firedantic import Model
from pydantic import BaseModel


class FieldItem(BaseModel):
    key: str
    value: Any


class FieldInput(BaseModel):
    name: str
    description: Optional[str] = None
    label: str
    dependent_on_field: Optional[str] = None
    dependent_on_field_value: Optional[Any] = None
    type: str
    conditionally_display_on_field: Optional[str] = None
    conditionally_display_on_field_value: Optional[Any] = None
    hide_text: bool
    items: Optional[List[FieldItem]] = []
    visible: bool
    required: bool


class Application(Model):
    __collection__ = 'apps'
    name: str
    label: str
    icon: Optional[str] = None
    required_inputs: Optional[List[FieldInput]] = []
    integration_id: Optional[str] = None
