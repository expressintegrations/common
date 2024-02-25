from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_pascal

from common.models.northtext.messages import MessageType, MessageStatus


class Tag(BaseModel):
    name: str
    value: str
    is_empty: Optional[bool] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class IncomingMessage(BaseModel):
    id: int
    sent_on: datetime
    number: Optional[str] = None
    contact_id: int
    message_type: MessageType
    message_status: MessageStatus
    body: Optional[str] = None
    attachment_url: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class DeliveryReceipt(BaseModel):
    processed_on: datetime
    finalized_on: datetime
    failed_on: datetime
    status: MessageStatus
    status_message: str
    body: Optional[str] = None
    attachment_url: Optional[str] = None
    number: Optional[str] = None
    mass_message_id: Optional[str] = None
    message_id: Optional[int] = None
    user_id: Optional[str] = None
    tags: Optional[List[Tag]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class OptInOptOut(int, Enum):
    OPTED_OUT = 0
    OPTED_IN = 1


class SubscriptionStatus(BaseModel):
    id: int
    sent_on: datetime
    number: Optional[str] = None
    contact_id: Optional[int] = None
    body: Optional[str] = None
    subscription_status: Optional[OptInOptOut] = None
    user_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class WebhookEventType(int, Enum):
    INCOMING_MESSAGE = 1
    DELIVERY_RECEIPT = 2
    JOB_COMPLETE = 3
    OPT_IN_OPT_OUT = 4


class WebhookCreateRequest(BaseModel):
    method: str
    url: str
    event: WebhookEventType


class Webhook(BaseModel):
    id: int
    method: str
    url: str
    event: WebhookEventType


class WebhookResponse(BaseModel):
    status: int
    description: str
    result: Webhook


class WebhookDeleteResponse(BaseModel):
    status: int
    description: str
    result: str
