from datetime import datetime
from enum import Enum

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
    major: int | None = None
    minor: int | None = None
    patch: int | None = None
    type: str | None = None


class Subscription(BaseModel):
    plan_id: str | None = None
    renewal_date: datetime | None = None
    is_trial: bool | None = None
    billing_period: str | None = None
    days_left: int | None = None
    pricing_version: int | None = None
    referrer: str | None = None
    referrer_slug: str | None = None
    max_units: int | None = None

    @field_serializer("renewal_date")
    def serialize_renewal_date(self, dt: datetime, _info):
        if dt is None:
            return None
        return dt.isoformat()


class AppEventData(BaseModel):
    app_id: int | None = None
    user_id: int | None = None
    user_email: str | None = None
    user_name: str | None = None
    user_cluster: str | None = None
    account_tier: str | None = None
    account_max_users: int | None = None
    account_id: int | None = None
    account_name: str | None = None
    account_slug: str | None = None
    version_data: VersionData | None = None
    timestamp: datetime | None = None
    subscription: Subscription | None = None
    user_country: str | None = None

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()


class AppEvent(BaseModel):
    type: EventType | None = None
    data: AppEventData | None = None
