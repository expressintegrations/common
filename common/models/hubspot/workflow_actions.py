from __future__ import annotations

from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel


class HubSpotExecutionState(str, Enum):
    SUCCESS = "SUCCESS"
    FAIL_CONTINUE = "FAIL_CONTINUE"
    BLOCK = "BLOCK"
    ASYNC = "ASYNC"


class WorkflowOptionsOrigin(BaseModel):
    portal_id: int
    action_definition_id: int
    action_definition_version: int
    action_execution_index_identifier: Optional[str] = None
    extension_definition_id: Optional[int] = None
    extension_definition_version_id: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class WorkflowFetchOptions(BaseModel):
    q: Optional[str] = None
    after: Optional[str] = None


class WorkflowOptionsRequest(BaseModel):
    origin: WorkflowOptionsOrigin
    input_field_name: str
    input_fields: dict
    fetch_options: Optional[WorkflowFetchOptions] = None
    object_type_id: str
    portal_id: int
    extension_definition_id: Optional[int] = None
    extension_definition_version: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class WorkflowFieldOption(BaseModel):
    label: str
    description: str
    value: str


class WorkflowOptionsResponse(BaseModel):
    options: List[WorkflowFieldOption]
    after: Optional[str] = None
    searchable: Optional[bool] = None


class HubSpotWorkflowActionOriginModel(BaseModel):
    portal_id: int
    action_definition_id: Optional[int] = None
    action_definition_version: Optional[int] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotWorkflowActionContextModel(BaseModel):
    source: Optional[str] = None
    workflow_id: int

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotWorkflowActionObjectModel(BaseModel):
    object_id: int
    object_type: str

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class MarketingEventType(str, Enum):
    SUCCESS = "WEBINAR"
    FAIL_CONTINUE = "CONFERENCE"
    BLOCK = "WORKSHOP"


class Operator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    NOT_STARTS_WITH = "not_starts_with"
    ENDS_WITH = "ends_with"
    NOT_ENDS_WITH = "not_ends_with"
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"


class HubSpotWorkflowActionInputFieldsModel(BaseModel):
    # hubspot_recruiting set default job form
    form_id: Optional[str] = None

    # hubspot_recruiting set default application data
    pipeline_id: Optional[str] = None
    stage_id: Optional[str] = None

    # hubspot_file_parser parse file
    source_property: Optional[str] = None
    destination_property: Optional[str] = None

    # hubspot_marketing_events subscriber state change
    external_event_id: Optional[str] = None
    subscriber_state: Optional[str] = None
    action_date_time_type: Optional[str] = None
    action_date_time_property: Optional[str] = None
    action_date_time: Optional[str] = None

    # hubspot_file_attachment_manager attach file
    file_property: Optional[str] = None
    destination_object_type: Optional[str] = None
    association_type: Optional[str] = None
    association_label: Optional[str] = None
    file_name_customization_type: Optional[str] = None
    text_to_append: Optional[str] = None
    new_file_name: Optional[str] = None
    access: Optional[str] = None

    # hubspot_file_attachment_manager delete attached files
    deletion_type: Optional[str] = None

    # hubspot_task_assistant
    from_owner_type: Optional[str] = None
    from_owner_property: Optional[str] = None
    from_owner: Optional[str] = None
    from_team: Optional[str] = None
    owner_type: Optional[str] = None
    owner_property: Optional[str] = None
    owner: Optional[str] = None
    team: Optional[str] = None
    task_status: Optional[str] = None
    task_type: Optional[List[str]] = None
    task_title_filter: Optional[bool] = None
    task_title_operator: Optional[Operator] = None
    task_title_value: Optional[str] = None
    task_title_case_sensitive: Optional[bool] = None
    include_deactivated_assigned: Optional[bool] = None
    include_deactivated_specific: Optional[bool] = None
    include_deactivated_team: Optional[bool] = None

    # fix my typo
    duplicate_behavior: Optional[str] = None

    # line item assistant
    product_id: Optional[int] = None
    quantity: Optional[float] = None
    price_type: Optional[str] = None
    price: Optional[float] = None
    price_property_value: Optional[str] = None
    products: Optional[List[str]] = None
    update_deal_amount: Optional[bool] = None
    create_if_none_match: Optional[bool] = None

    # growth ops apps
    property_value: Optional[Any] = None
    operator: Optional[Operator] = None


class HubSpotWorkflowActionInputModel(BaseModel):
    callback_id: str
    origin: HubSpotWorkflowActionOriginModel
    context: HubSpotWorkflowActionContextModel
    object: HubSpotWorkflowActionObjectModel
    input_fields: HubSpotWorkflowActionInputFieldsModel

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class ErrorCode(str, Enum):
    INVALID_SUBSCRIPTION = "INVALID_SUBSCRIPTION"
    INVALID_PROPERTY_VALUE = "INVALID_PROPERTY_VALUE"
    INVALID_EVENT = "INVALID_EVENT"
    INVALID_FILE_ACCESS = "INVALID_FILE_ACCESS"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    LINE_ITEMS_NOT_FOUND = "LINE_ITEMS_NOT_FOUND"


class HubSpotWorkflowActionOutputFieldsModel(BaseModel):
    error_code: Optional[ErrorCode] = Field(default=None, alias='errorCode')
    hs_execution_state: HubSpotExecutionState
    hs_expiration_duration: Optional[str] = None
    attempted_correction: Optional[str] = None
    result: Optional[str] = None

    class Config:
        populate_by_name = True


class HubSpotWorkflowActionOutputModel(BaseModel):
    output_fields: HubSpotWorkflowActionOutputFieldsModel

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class HubSpotWorkflowActionCallbackModel(BaseModel):
    output_fields: HubSpotWorkflowActionOutputFieldsModel
    callback_id: str = Field(default=None, alias='callbackId')

    class Config:
        populate_by_name = True


class HubSpotWorkflowActionCallbackBatchModel(BaseModel):
    inputs: List[HubSpotWorkflowActionCallbackModel]

    class Config:
        populate_by_name = True


class HubSpotWorkflowException(Exception):
    def __init__(self, error_code: ErrorCode, message: str):
        self.error_code = error_code
        self.message = message

    def __str__(self):
        return self.message
