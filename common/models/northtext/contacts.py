from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Gender(int, Enum):
    FEMALE = 0
    MALE = 1


class ContactCreateRequest(BaseModel):
    phone_number: Optional[str] = None
    name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[Gender] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    is_subscriber: Optional[bool] = None
    groups: Optional[List[int]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class OptOutStatus(str, Enum):
    SUBSCRIBED = "Subscribed"
    OPTED_OUT = "Opted Out"
    NOT_SUBSCRIBED = "Not Subscribed"


class Contact(BaseModel):
    phone_number: Optional[str] = None
    name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[Gender] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    is_subscriber: bool = None
    groups: Optional[List[int]] = None
    id: int = None
    creation_date: datetime = None
    last_update: datetime = None
    status: Optional[OptOutStatus] = None
    subscribed_date: Optional[datetime] = None
    unsubscribed_date: Optional[datetime] = None


class ContactResponse(BaseModel):
    status: int
    description: str
    result: Contact


class ContactsResponse(BaseModel):
    status: int
    description: str
    result: Optional[List[Contact]] = None
