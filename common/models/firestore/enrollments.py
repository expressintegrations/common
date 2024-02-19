from datetime import datetime
from typing import List

from pydantic import BaseModel


class BulkEnrollment(BaseModel):
    timestamp: datetime
    callback_ids: List[str]
    request: dict
    processing: bool
    action_taken: bool
    usage_reported: bool
    completed: bool
    expires: datetime
