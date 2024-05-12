from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Plan(BaseModel):
    max_users: int
    period: str
    tier: str
    version: int


class Kind(str, Enum):
    CORE = "core"
    MARKETING = "marketing"
    CRM = "crm"
    SOFTWARE = "software"
    FORMS = "forms"
    WHITEBOARD = "whiteboard"
    PROJECT_MANAGEMENT = "project_management"


class AccountProduct(BaseModel):
    id: int
    kind: Kind


class Account(BaseModel):
    country_code: Optional[str] = None
    id: Optional[int] = None
    name: Optional[str] = None
    plan: Optional[Plan] = None
    products: Optional[List[AccountProduct]] = None
    slug: Optional[str] = None
    tier: Optional[str] = None
