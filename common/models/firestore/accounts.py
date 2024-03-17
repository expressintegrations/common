from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Account(BaseModel):
    name: str
    account_identifier: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    hs_company_id: Optional[str] = None
    created_at: Optional[datetime] = None
    active: Optional[bool] = None
    source: Optional[dict] = None
