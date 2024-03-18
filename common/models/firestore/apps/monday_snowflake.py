from datetime import datetime, timedelta
from typing import Optional

from firedantic import Model


class MondayObject(Model):
    __collection__ = "apps/monday_snowflake/monday_objects"
    __ttl_field__ = "timestamp"

    timestamp: Optional[datetime] = datetime.now() + timedelta(minutes=10)
    object_id: Optional[str] = None
    content: Optional[str] = None
