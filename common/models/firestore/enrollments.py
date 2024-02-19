from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel


class BulkEnrollmentStatus(str, Enum):
    QUEUED = 'queued'
    PROCESSING = 'processing'
    DONE = 'done'


class BulkEnrollment(BaseModel):
    timestamp: datetime
    callback_ids: List[str]
    request: dict
    completed: bool
    expires: datetime
    status: BulkEnrollmentStatus
