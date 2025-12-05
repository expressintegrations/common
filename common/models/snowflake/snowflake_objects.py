from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from firedantic import AsyncModel


class SnowflakeObject(AsyncModel):
    __collection__ = "apps/snowflake/snowflake_objects"
    __ttl_field__ = "timestamp"

    timestamp: Optional[datetime] = datetime.now(tz=timezone.utc) + timedelta(
        minutes=10
    )
    content: Optional[Any] = None
