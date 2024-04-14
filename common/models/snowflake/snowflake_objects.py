from datetime import datetime, timedelta
from typing import Optional, Any

from firedantic import Model


class SnowflakeObject(Model):
    __collection__ = "apps/snowflake/snowflake_objects"
    __ttl_field__ = "timestamp"

    timestamp: Optional[datetime] = datetime.now() + timedelta(minutes=10)
    content: Optional[Any] = None
