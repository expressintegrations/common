from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Reference(BaseModel):
    title: Optional[str] = None
    value: Optional[Any] = None
    invalid: Optional[bool] = None


class InboundFieldValues(BaseModel):
    board_id: Optional[int] = None
    table: Optional[Reference] = None
    table_column: Optional[Reference] = None
    monday_column_id: Optional[Reference] = None
    boolean_column: Optional[Reference] = None
    boolean_value: Optional[Reference] = None
    schema: Optional[Reference] = None
    table_name: Optional[str] = None
    item_id: Optional[int] = None
    error_column_id: Optional[str] = None
    row: Optional[dict] = None
    workspace: Optional[Reference] = None
    item_values: Optional[dict] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class IntegrationRun(BaseModel):
    block_kind: Optional[str] = None
    recipe_id: Optional[int] = None
    integration_id: Optional[int] = None
    inbound_field_values: Optional[InboundFieldValues] = None
    account_id: Optional[int] = None
    user_id: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class RuntimeMetadata(BaseModel):
    action_uuid: Optional[str] = None
    trigger_uuid: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class ActionPayload(BaseModel):
    payload: Optional[IntegrationRun] = None
    runtime_metadata: Optional[RuntimeMetadata] = None
