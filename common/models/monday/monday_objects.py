from datetime import datetime, timedelta
from typing import Optional, Any

from firedantic import Model


class MondayObject(Model):
    __collection__ = "apps/monday_snowflake/monday_objects"
    __ttl_field__ = "timestamp"

    timestamp: Optional[datetime] = datetime.now() + timedelta(minutes=10)
    content: Optional[Any] = None
