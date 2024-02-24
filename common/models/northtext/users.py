from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class User(BaseModel):
    id: int
    phone_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    forward_to_phone: Optional[bool] = None
    forward_to_email: Optional[bool] = None
    active: Optional[bool] = None
    password: Optional[str] = None
    default_system_number: Optional[int] = None
    creation_date: Optional[datetime] = None
    last_update: Optional[datetime] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class UsersResponse(BaseModel):
    status: int
    description: str
    result: Optional[List[User]] = None
