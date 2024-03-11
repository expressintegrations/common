from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class InboundFieldValues(BaseModel):
    board_id: Optional[int] = None
    table: Optional[str] = None
    schema: Optional[str] = None
    table_name: Optional[str] = None
    item_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class IntegrationRun(BaseModel):
    recipe_id: int
    integration_id: int
    inbound_field_values: InboundFieldValues

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class Payload(BaseModel):
    payload: IntegrationRun
