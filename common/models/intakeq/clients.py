from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_pascal


class BillingType(int, Enum):
    UNKNOWN = 0
    SELF_PAY = 1
    INSURANCE = 2


class RelationshipType(int, Enum):
    NONE = 0
    PARENT = 1
    CHILD = 2
    SPOUSE = 2
    SIBLING = 2
    OTHER = 2
    PARTNER = 2


class LinkedClient(BaseModel):
    client_number: Optional[int] = None
    relationship_type: Optional[RelationshipType] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class CustomField(BaseModel):
    field_id: Optional[str] = None
    text: Optional[str] = None
    value: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Client(BaseModel):
    client_id: Optional[int] = None
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[int] = None
    marital_status: Optional[str] = None
    gender: Optional[str] = None
    tags: Optional[List[str]] = None
    archived: Optional[bool] = None
    home_phone: Optional[str] = None
    work_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[str] = None
    unit_number: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state_short: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    additional_information: Optional[str] = None
    billing_type: Optional[int] = None
    primary_insurance_company: Optional[str] = None
    primary_insurance_policy_number: Optional[str] = None
    primary_insurance_group_number: Optional[str] = None
    primary_insurance_holder_name: Optional[str] = None
    primary_insurance_relationship: Optional[str] = None
    primary_insurance_holder_date_of_birth: Optional[int] = None
    secondary_insurance_company: Optional[str] = None
    secondary_insurance_policy_number: Optional[str] = None
    secondary_insurance_group_number: Optional[str] = None
    secondary_insurance_holder_name: Optional[str] = None
    secondary_insurance_relationship: Optional[str] = None
    secondary_insurance_holder_date_of_birth: Optional[int] = None
    date_created: Optional[int] = None
    last_activity_date: Optional[int] = None
    last_update_date: Optional[int] = None
    stripe_customer_id: Optional[str] = None
    square_customer_id: Optional[str] = None
    external_client_id: Optional[str] = None
    credit_balance: Optional[float] = None
    last_activity_name: Optional[str] = None
    parent_client_id: Optional[int] = None
    linked_clients: Optional[List[LinkedClient]] = None
    custom_fields: Optional[List[CustomField]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Tag(BaseModel):
    client_id: Optional[int] = None
    tag: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Diagnosis(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    note_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal
