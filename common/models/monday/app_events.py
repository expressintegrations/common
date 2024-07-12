from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_serializer


class EventType(str, Enum):
    INSTALL = "install"
    UNINSTALL = "uninstall"
    CREATED = "app_subscription_created"
    CHANGED = "app_subscription_changed"
    CANCELLED_BY_USER = "app_subscription_cancelled_by_user"
    RENEWED = "app_subscription_renewed"
    CANCELLED = "app_subscription_cancelled"
    CANCELLATION_REVOKED_BY_USER = "app_subscription_cancellation_revoked_by_user"
    RENEWAL_ATTEMPT_FAILED = "app_subscription_renewal_attempt_failed"
    RENEWAL_FAILED = "app_subscription_renewal_failed"
    TRIAL_SUBSCRIPTION_STARTED = "app_trial_subscription_started"
    TRIAL_SUBSCRIPTION_ENDED = "app_trial_subscription_ended"


class VersionData(BaseModel):
    major: int
    minor: int
    patch: int
    type: str


class Subscription(BaseModel):
    plan_id: str
    renewal_date: datetime
    is_trial: bool
    billing_period: str
    days_left: int
    pricing_version: int


class AppEventData(BaseModel):
    app_id: int
    user_id: int
    user_email: str
    user_name: str
    user_cluster: str
    account_tier: str
    account_max_users: int
    account_id: int
    account_name: str
    account_slug: str
    version_data: Optional[VersionData] = None
    timestamp: datetime
    subscription: Optional[Subscription] = None
    user_country: str

    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime, _info):
        return timestamp.isoformat()


class AppEvent(BaseModel):
    type: Optional[EventType] = None
    data: Optional[AppEventData] = None
