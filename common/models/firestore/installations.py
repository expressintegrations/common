from datetime import datetime, timezone
from typing import List, Optional

from firedantic import AsyncModel
from pydantic import BaseModel


class Output(BaseModel):
    name: str
    url: str


class Installation(AsyncModel):
    __collection__ = "installations"
    integration_name: Optional[str] = None
    account_identifier: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    installed_by_id: Optional[str] = None
    subscription_id: Optional[str] = None
    hs_deal_id: Optional[str] = None
    price_id: Optional[str] = None
    attempted_feature_id: Optional[str] = None
    active: Optional[bool] = False
    installation_in_progress: Optional[bool] = False
    installed_at: Optional[datetime] = None
    created_at: Optional[datetime] = datetime.now(tz=timezone.utc)
    uninstalled_at: Optional[datetime] = None
    uninstallation_in_progress: Optional[bool] = False
    activated_at: Optional[datetime] = None
    back_to_url: Optional[str] = None
    step_completed: Optional[int] = 0
    final_output: Optional[List[Output]] = None
    metadata: Optional[dict] = None
