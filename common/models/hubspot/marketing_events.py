from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, field_serializer
from pydantic.alias_generators import to_camel


class MarketingEvent(BaseModel):
    event_name: str
    event_description: Optional[str] = None
    event_url: Optional[str] = None
    event_type: Optional[str] = None
    start_date_time: Optional[str] = None
    end_date_time: Optional[str] = None
    event_organizer: str
    external_account_id: str
    external_event_id: str
    custom_properties: Optional[dict]

    class Config:
        populate_by_name = True
        alias_generator = to_camel

    @field_serializer('custom_properties')
    def serialize_custom_properties(self, data: dict, _info):
        now = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
        return [
            {
                "name": k,
                "value": v,
                "timestamp": now,
                "sourceId": "express_integrations_marketing_events",
                "sourceLabel": "Express Integrations Marketing Events",
                "source": "API"
            } for k, v in data.items()
        ] if data else None


class Registration(BaseModel):
    portal_id: int
    external_event_id: str
    contact_id: int
    subscriber_state: str
    timestamp: int
