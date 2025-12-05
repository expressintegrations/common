from datetime import datetime, timezone
from typing import List, Optional

from firedantic import AsyncModel

from common.models.monday.app_events import Subscription as MondaySubscription


class Subscription(AsyncModel):
    __collection__ = "subscriptions"
    account_id: Optional[str] = None
    stripe_id: Optional[str] = None
    installation_ids: Optional[List[str]] = None
    hs_subscription_id: Optional[str] = None
    price_ids: Optional[List[str]] = None
    active: Optional[bool] = False
    is_trial: Optional[bool] = False
    created_at: datetime = datetime.now(tz=timezone.utc)
    ended_at: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = False
    checkout_session_id: Optional[str] = None
    stripe_object: Optional[dict] = None
    monday_object: Optional[MondaySubscription] = None
