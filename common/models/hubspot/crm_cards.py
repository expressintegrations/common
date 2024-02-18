from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class HubSpotCRMCardActionType(str, Enum):
    IFRAME = "IFRAME"
    ACTION_HOOK = "ACTION_HOOK"
    CONFIRMATION_ACTION_HOOK = "CONFIRMATION_ACTION_HOOK"


class HubSpotCRMCardActionModel(BaseModel):
    type: HubSpotCRMCardActionType
    width: Optional[int] = None
    height: Optional[int] = None
    uri: str
    label: str
    associated_object_properties: Optional[List[str]] = None
    confirmation_message: Optional[str] = None
    confirm_button_text: Optional[str] = None
    cancel_button_text: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotCRMCardModel(BaseModel):
    results: Optional[List]
    primary_action: HubSpotCRMCardActionModel

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class TopLevelAction(BaseModel):
    type: HubSpotCRMCardActionType
    width: Optional[int] = None
    height: Optional[int] = None
    url: str
    label: str
    property_names_included: Optional[List[str]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class TopLevelActions(BaseModel):
    settings: Optional[TopLevelAction]
    primary: Optional[TopLevelAction]
    secondary: Optional[List[TopLevelAction]]


class Token(BaseModel):
    name: str
    label: str
    dataType: str
    value: Any


class Action(BaseModel):
    type: str = "ACTION_HOOK"
    confirmation: Optional[str] = None
    http_method: str
    url: str
    label: str
    property_names_included: Optional[List[str]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class Section(BaseModel):
    id: str
    title: str
    link_url: Optional[str] = None
    tokens: Optional[List[Token]]
    actions: Optional[List[Action]]

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class CRMCard(BaseModel):
    response_version: str = "v3"
    all_items_link_url: str
    card_label: str
    top_level_actions: Optional[TopLevelActions]
    sections: Optional[List[Section]]

    class Config:
        populate_by_name = True
        alias_generator = to_camel
