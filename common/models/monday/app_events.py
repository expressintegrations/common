from enum import Enum
from typing import Optional

from pydantic import BaseModel


class EventType(str, Enum):
    INSTALL = "install"
    UNINSTALL = "uninstall"
    APP_SUBSCRIPTION_CREATED = "app_subscription_created"
    APP_SUBSCRIPTION_CHANGED = "app_subscription_changed"
    APP_SUBSCRIPTION_CANCELLED = "app_subscription_cancelled_by_user"
    APP_SUBSCRIPTION_RENEWED = "app_subscription_renewed"


class VersionData(BaseModel):
    major: Optional[int] = None
    minor: Optional[int] = None
    patch: Optional[int] = None
    type: Optional[str] = None


class Subscription(BaseModel):
    plan_id: Optional[str] = None
    renewal_date: Optional[str] = None
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
    version_data: Optional[VersionData] = None
    timestamp: Optional[str] = None
    subscription: Optional[Subscription] = None


class AppEvent(BaseModel):
    type: Optional[EventType] = None
    data: Optional[AppEventData] = None
