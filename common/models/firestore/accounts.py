from datetime import datetime, timezone
from typing import Optional

from firedantic import AsyncModel
from pydantic import BaseModel

from common.models.firestore.multi_model import (
    MultiLevelAsyncSubCollection,
    MultiLevelAsyncSubModel,
)


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


class AppAccount(MultiLevelAsyncSubModel):
    created: datetime
    current_usage: int | None = None

    class Collection(MultiLevelAsyncSubCollection):
        __collection_tpl__ = "apps/{app_id}/accounts"


class NorthTextAccount(AppAccount):
    inbound_sms_webhook_id: int | None = None
    inbound_sms: bool | None = None
    outbound_sms_webhook_id: int | None = None
    outbound_sms: bool | None = None
    subscription_status_webhook_id: int | None = None
    subscription_status: bool | None = None
