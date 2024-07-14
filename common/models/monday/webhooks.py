from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_serializer
from pydantic.alias_generators import to_camel

from common.models.monday.monday_integrations import InputFields


class MondayWebhookEvent(BaseModel):
    user_id: Optional[int] = None
    original_trigger_uuid: Optional[str] = None
    board_id: Optional[int] = None
    pulse_id: Optional[int] = None
    pulse_name: Optional[str] = None
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    group_color: Optional[str] = None
    is_top_group: Optional[bool] = None
    column_values: Optional[Dict[str, Any]] = None
    app: Optional[str] = None
    type: Optional[str] = None
    trigger_time: Optional[datetime] = None
    subscription_id: Optional[int] = None
    trigger_uuid: Optional[str] = None
    column_id: Optional[str] = None
    column_type: Optional[str] = None
    column_title: Optional[str] = None
    value: Optional[Any] = None
    previous_value: Optional[Any] = None
    changed_at: Optional[float] = None

    @field_serializer('trigger_time')
    def serialize_trigger_time(self, trigger_time: datetime, _info):
        return trigger_time.isoformat()

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class MondayWebhook(BaseModel):
    challenge: Optional[str] = None
    event: Optional[MondayWebhookEvent] = None


class SubscriptionRequest(BaseModel):
    integration_id: Optional[int] = None
    subscription_id: Optional[int] = None
    recipe_id: Optional[int] = None
    webhook_url: Optional[str] = None
    input_fields: Optional[InputFields] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class SubscriptionRequestPayload(BaseModel):
    payload: SubscriptionRequest


class UnsubscribeRequest(BaseModel):
    id: Optional[int] = None
    webhook_id: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class UnsubscribeRequestPayload(BaseModel):
    payload: UnsubscribeRequest
