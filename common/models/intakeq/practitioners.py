from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_pascal


class Role(str, Enum):
    ADMINISTRATOR = "Administrator"
    PRACTITIONER = "Practitioner"


class Practitioner(BaseModel):
    id: Optional[str] = None
    complete_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    date_created: Optional[datetime] = None
    external_practitioner_id: Optional[str] = None
    role_name: Optional[Role] = None
    npi: Optional[str] = None
    is_inactive: Optional[bool] = None
    additional_practitioner_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal
