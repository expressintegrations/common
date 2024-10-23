from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubscriptionStatus(BaseModel):
    billing_period: Optional[str] = None
    days_left: Optional[int] = None
    is_trial: Optional[bool] = None
    plan_id: Optional[str] = None
    renewal_date: Optional[datetime] = None
