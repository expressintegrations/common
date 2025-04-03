from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, field_serializer
from pydantic.alias_generators import to_camel


class AppInfo(BaseModel):
    id: str
    name: str


class MarketingEvent(BaseModel):
    event_name: str
    event_description: Optional[str] = None
    event_url: Optional[str] = None
    event_type: Optional[str] = None
    start_date_time: Optional[str] = None
    end_date_time: Optional[str] = None
    event_organizer: Optional[str] = None
    external_account_id: Optional[str] = None
    external_event_id: Optional[str] = None
    custom_properties: Optional[list | dict] = None
    event_cancelled: Optional[bool] = None
    event_completed: Optional[bool] = None
    object_id: Optional[str] = None
    event_status: Optional[str] = None
    app_info: Optional[AppInfo] = None
    registrants: Optional[int] = None
    attendees: Optional[int] = None
    cancellations: Optional[int] = None
    no_shows: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel

    @field_serializer("custom_properties")
    def serialize_custom_properties(self, data: dict, _info):
        now = int(datetime.now().timestamp() * 1000)
        return (
            [
                {
                    "name": k,
                    "value": v,
                    "timestamp": now,
                    "sourceId": "growth_operations_marketing_events",
                    "sourceLabel": "Growth Operations Marketing Events",
                    "source": "API",
                }
                for k, v in data.items()
            ]
            if data
            else None
        )


class SubscriberState(str, Enum):
    REGISTERED = "register"
    ATTENDED = "attend"
    CANCELLED = "cancel"
    NO_SHOW = "no_show"


class Registration(BaseModel):
    portal_id: int
    external_event_id: str
    contact_id: int
    subscriber_state: SubscriberState
    timestamp: int


class RegistrationV2(BaseModel):
    portal_id: int
    internal_event_id: str
    contact_id: int
    subscriber_state: SubscriberState
    timestamp: int


class Next(BaseModel):
    after: str
    link: str


class Paging(BaseModel):
    next: Next


class MarketingEventResultsWithPaging(BaseModel):
    results: List[MarketingEvent]
    paging: Optional[Paging] = None
