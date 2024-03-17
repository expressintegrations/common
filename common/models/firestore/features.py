from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Feature(BaseModel):
    name: str
    integration_id: str
    external_id: Optional[str] = None
    version: Optional[str] = None
    feature_group_id: str
