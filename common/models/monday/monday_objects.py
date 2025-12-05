from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from firedantic import AsyncModel


class MondayObject(AsyncModel):
    __collection__ = "apps/monday_snowflake/monday_objects"
    __ttl_field__ = "timestamp"

    timestamp: Optional[datetime] = datetime.now(tz=timezone.utc) + timedelta(
        minutes=10
    )
    content: Optional[Any] = None
