from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from enum import Enum


class SubscriptionType(str, Enum):
    OBJECT_CREATION = "object.creation"
    OBJECT_DELETION = "object.deletion"
    OBJECT_PROPERTY_CHANGE = "object.propertyChange"
    OBJECT_MERGE = "object.merge"
    OBJECT_RESTORE = "object.restore"
    OBJECT_ASSOCIATION_CHANGE = "object.associationChange"


class HubSpotAppWebhookEvent(BaseModel):
    event_id: Optional[int] = None
    event_type: Optional[str] = None
    subscription_id: Optional[int] = None
    portal_id: Optional[int] = None
    app_id: Optional[int] = None
    occurred_at: Optional[int] = None
    subscription_type: Optional[SubscriptionType] = None
    attempt_number: Optional[int] = None
    change_source: Optional[str] = None
    association_type_id: Optional[int] = None
    association_category: Optional[str] = None
    from_object_type_id: Optional[str] = None
    from_object_id: Optional[int] = None
    to_object_type_id: Optional[str] = None
    to_object_id: Optional[int] = None
    association_removed: Optional[bool] = None
    is_primary_association: Optional[bool] = None
    primary_object_id: Optional[int] = None
    merged_object_ids: Optional[List[int]] = None
    new_object_id: Optional[int] = None
    number_of_properties_moved: Optional[int] = None
    object_id: Optional[int] = None
    object_type_id: Optional[str] = None
    property_name: Optional[str] = None
    property_value: Optional[str] = None
    message_id: Optional[int] = None
    message_type: Optional[str] = None
    source_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotWorkflowWebhookEvent(BaseModel):
    portal_id: Optional[int] = None
    object_type_id: Optional[str] = None
    object_id: Optional[int] = None
    properties: Optional[dict]

    class Config:
        populate_by_name = True
        alias_generator = to_camel
