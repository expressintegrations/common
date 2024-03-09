from datetime import datetime

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Account(BaseModel):
    id: str
    creation_date: datetime
    last_update: datetime
    first_name: str
    last_name: str
    email: str
    company: str
    timezone: str
    forward_to_phone: str
    forward_to_email: str
    active: bool
    default_system_number: int

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class AccountResponse(BaseModel):
    status: int
    description: str
    result: Account
