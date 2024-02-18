from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class HubSpotSettingsIframeModel(BaseModel):
    iframeUrl: str


class HubSpotSettingsIframeResponseModel(BaseModel):
    response: HubSpotSettingsIframeModel


class HubSpotAppSettingsActionTypeModel(str, Enum):
    ACCOUNTS_FETCH = "ACCOUNTS_FETCH"
    BUTTON_UPDATE = "BUTTON_UPDATE"
    IFRAME_FETCH = "IFRAME_FETCH"
    TOGGLE_FETCH = "TOGGLE_FETCH"
    TOGGLE_UPDATE = "TOGGLE_UPDATE"
    DROPDOWN_FETCH = "DROPDOWN_FETCH"
    DROPDOWN_UPDATE = "DROPDOWN_UPDATE"


class HubSpotSettingsToggleStatusModel(BaseModel):
    enabled: bool


class HubSpotSettingsToggleUpdateModel(BaseModel):
    response: HubSpotSettingsToggleStatusModel
    message: Optional[str]


class HubSpotAppSettingsModel(BaseModel):
    action_type: HubSpotAppSettingsActionTypeModel
    app_id: int
    portal_id: int
    user_id: int
    user_email: str
    account_id: Optional[str] = None
    enabled: Optional[bool] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotAccountSettingsModel(BaseModel):
    account_id: str
    account_name: Optional[str] = None
    account_logo_url: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotSettingsAccountListModel(BaseModel):
    accounts: List[HubSpotAccountSettingsModel]


class HubSpotAccountsFetchResponseModel(BaseModel):
    response: HubSpotSettingsAccountListModel


class HubSpotAccountDetails(BaseModel):
    portal_id: int
    account_type: str
    time_zone: str
    company_currency: str
    additional_currencies: List[str]
    utc_offset: str
    utc_offset_milliseconds: int
    ui_domain: str
    data_hosting_location: str

    class Config:
        populate_by_name = True
        alias_generator = to_camel
