from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, field_serializer
from pydantic.alias_generators import to_camel


class Tag(BaseModel):
    name: str
    value: str
    is_empty: Optional[bool] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class MessageSendRequest(BaseModel):
    body: Optional[str]
    shorten_links: Optional[bool] = None
    attachment: Optional[str] = None
    attachment_type: Optional[str] = None
    attachment_url: Optional[str] = None
    send_on: Optional[datetime] = None
    to: Optional[List[str]] = None
    drip_campaign: Optional[int] = None
    system_number: Optional[int] = None
    tags: Optional[List[Tag]] = None

    @field_serializer('send_on')
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class MessageType(int, Enum):
    SMS = 1
    MMS = 2


class MessageStatus(int, Enum):
    NEW = 0
    QUEUED = 1
    DELIVERED = 2
    FAILED = 3
    RECEIVED = 4
    PROCESSED = 5


class Message(BaseModel):
    id: int
    sent_on: str = None
    number: Optional[str] = None
    contact_id: int = None
    message_type: MessageType = None
    message_status: MessageStatus = None
    body: Optional[str] = None
    attachment_url: Optional[str] = None
    user_id: Optional[str] = None
    tags: Optional[List[Tag]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class MessageResponse(BaseModel):
    status: int
    description: str
    result: Optional[List[Message]] = None


class MessagesResponse(BaseModel):
    status: int
    description: str
    result: Optional[List[Message]] = None


class BulkMessagesResponse(BaseModel):
    status: int
    description: str
    job: int
