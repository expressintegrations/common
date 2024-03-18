from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Reference(BaseModel):
    value: Any


class InboundFieldValues(BaseModel):
    board_id: Optional[int] = None
    table: Optional[Reference] = None
    table_column: Optional[Reference] = None
    boolean_column: Optional[Reference] = None
    boolean_value: Optional[Reference] = None
    schema: Optional[str] = None
    table_name: Optional[str] = None
    item_id: Optional[str] = None
    error_column_id: Optional[str] = None
    row: Optional[dict] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class IntegrationRun(BaseModel):
    recipe_id: int
    integration_id: int
    inbound_field_values: InboundFieldValues
    account_id: Optional[int] = None
    user_id: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class ActionPayload(BaseModel):
    payload: IntegrationRun
