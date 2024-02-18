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
    # hubspot_northtext
    recipient: str
    static_phone: Optional[str]
    phone_property: Optional[str]
    sms_body: str
    image: Optional[str]
    tag: Optional[str]

    # express integrations
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
    MISSING_PHONE = "MISSING_PHONE"
    INVALID_PHONE = "INVALID_PHONE"
    SMS_SEND_FAILURE = "SMS_SEND_FAILURE"


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
