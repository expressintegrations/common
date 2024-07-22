from datetime import datetime
from enum import Enum
from typing import List, Any
from typing import Optional

from firedantic import Model
from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class Reference(BaseModel):
    title: Optional[str] = None
    value: Optional[Any] = None
    invalid: Optional[bool] = None


class SchedulerType(str, Enum):
    DAILY = 'Daily'
    WEEKLY = 'Weekly'
    MONTHLY = 'Monthly'


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
    scheduler_config: Optional[SchedulerConfig] = None
    status_column_value: Optional[StatusColumnValue] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


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
    last_successful_run_at: Optional[datetime] = None
    installation_id: Optional[str] = None
    initial_run_completed: Optional[bool] = False
