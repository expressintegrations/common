from typing import Any, Dict, List, Optional

from firedantic import AsyncModel
from pydantic import BaseModel


class FieldItem(BaseModel):
    key: str
    value: Any


class FieldInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    dependent_field_values: Optional[Dict[str, List[FieldItem]]] = None
    dependent_on_field: Optional[str] = None
    dependent_on_field_value: Optional[Any] = None
    type: Optional[str] = None
    conditionally_display_on_field: Optional[str] = None
    conditionally_display_on_field_value: Optional[Any] = None
    hide_text: Optional[bool] = None
    items: Optional[List[FieldItem]] = []
    visible: Optional[bool] = None
    required: Optional[bool] = None
    display_order: Optional[int] = None


class Application(AsyncModel):
    __collection__ = "apps"
    name: str
    label: str
    icon: Optional[str] = None
    required_inputs: Optional[List[FieldInput]] = []
    integration_id: Optional[str] = None
    requires_user_auth: Optional[bool] = None
    ip_ranges: List[str] = []
