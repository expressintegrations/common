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
    major: Optional[int] = None
    minor: Optional[int] = None
    patch: Optional[int] = None
    type: Optional[str] = None


class Subscription(BaseModel):
    plan_id: Optional[str] = None
    renewal_date: Optional[datetime] = None
    is_trial: Optional[bool] = None
    billing_period: Optional[str] = None
    days_left: Optional[int] = None
    pricing_version: Optional[int] = None


class AppEventData(BaseModel):
    app_id: Optional[int] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    user_cluster: Optional[str] = None
    account_tier: Optional[str] = None
    account_max_users: Optional[int] = None
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    account_slug: Optional[str] = None
    version_data: Optional[VersionData] = None
    timestamp: Optional[datetime] = None
    subscription: Optional[Subscription] = None
    user_country: Optional[str] = None

    @field_serializer('timestamp')
    def serialize_timestamp(self, timestamp: datetime, _info):
        return timestamp.isoformat()


class AppEvent(BaseModel):
    type: Optional[EventType] = None
    data: Optional[AppEventData] = None
