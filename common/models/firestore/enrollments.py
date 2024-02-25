from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BulkEnrollment(BaseModel):
    timestamp: Optional[datetime] = None
    callback_ids: Optional[List[str]] = None
    request: Optional[dict] = None
    action_taken: Optional[bool] = None
    usage_reported: Optional[bool] = None
    completed: Optional[bool] = None
    expires: Optional[datetime] = None
    job_id: Optional[int] = None
