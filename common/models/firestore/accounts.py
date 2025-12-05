from datetime import datetime, timezone
from typing import Optional

from firedantic import AsyncModel
from pydantic import BaseModel


class AccountSource(BaseModel):
    integration_name: str


class Account(AsyncModel):
    __collection__ = "accounts"
    name: Optional[str] = None
    account_identifier: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    hs_company_id: Optional[str] = None
    created_at: Optional[datetime] = datetime.now(tz=timezone.utc)
    active: Optional[bool] = None
    source: Optional[AccountSource] = None
    monday_account_id: Optional[int] = None
    monday_account_slug: Optional[str] = None
