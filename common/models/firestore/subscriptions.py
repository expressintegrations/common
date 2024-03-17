from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class Subscription(BaseModel):
    account: str
    stripe_id: Optional[str] = None
    installation_ids: Optional[List[str]] = None
    price_ids: List[str] = None
    active: Optional[bool] = False
    is_trial: Optional[bool] = False
    created_at: datetime = datetime.now()
    ended_at: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = False
    checkout_session_id: Optional[str] = None
    stripe_object: Optional[dict] = None
    attempted_feature_id: Optional[str] = None
