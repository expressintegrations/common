from datetime import datetime, UTC
from enum import Enum
from typing import List, Any
from typing import Optional

from firedantic import Model, SubCollection, SubModel
from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from common.models.monday.integration_runs import InboundFieldValues


class Reference(BaseModel):
    title: Optional[str] = None
    value: Optional[Any] = None
    invalid: Optional[bool] = None


class SchedulerType(str, Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


class SchedulerConfig(BaseModel):
    days: Optional[List[str]] = None
    hour: Optional[str] = None
    type: Optional[SchedulerType] = None
    invalid: Optional[bool] = None
    timezone: Optional[str] = None
    occurrences: Optional[str] = None


class StatusColumnValue(BaseModel):
    index: Optional[int] = None


class InputFields(BaseModel):
    board_id: Optional[int] = None
    column_id: Optional[str] = None
    time: Optional[Reference] = None
    hours: Optional[Reference] = None
    table: Optional[Reference] = None
    filter_column: Optional[Reference] = None
    filter_value: Optional[str] = None
    scheduler_config: Optional[SchedulerConfig] = None
    status_column_value: Optional[StatusColumnValue] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class IntegrationRunStatus(str, Enum):
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"


class MondayIntegration(Model):
    __collection__ = "monday_integrations"
    integration_id: Optional[int] = None
    account_id: Optional[int] = None
    subscription_id: Optional[int] = None
    user_id: Optional[int] = None
    webhook_url: Optional[str] = None
    feature_id: Optional[str] = None
    feature_group_id: Optional[str] = None
    input_fields: Optional[InputFields] = None
    webhook_id: Optional[int] = None
    installation_id: Optional[str] = None
    initial_run_completed: Optional[bool] = False
    field_map: Optional[dict[str, str]] = None
    inbound_field_values: Optional[InboundFieldValues] = None
    recipe_id: Optional[int] = None
    board_name: Optional[str] = None
    recipe_name: Optional[str] = None
    last_successful_run_at: Optional[datetime] = None
    last_run_status: Optional[IntegrationRunStatus] = None
    last_run_at: Optional[datetime] = None
    last_run_error_message: Optional[str] = None
    last_run_total_rows: Optional[int] = None
    last_run_processed_rows: Optional[int] = None


class IntegrationHistory(SubModel):
    run_status: Optional[IntegrationRunStatus] = None
    run_started_at: Optional[datetime] = None
    run_completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None

    class Collection(SubCollection):
        __collection_tpl__ = "monday_integrations/{id}/history"
