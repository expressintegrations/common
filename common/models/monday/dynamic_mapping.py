from typing import List

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class FieldOption(BaseModel):
    id: str
    title: str
    outbound_type: str
    inbound_types: List[str]

    class Config:
        populate_by_name = True
        alias_generator = to_camel
