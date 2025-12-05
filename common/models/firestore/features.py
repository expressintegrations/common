from enum import Enum
from typing import Optional

from firedantic import AsyncModel


class FeatureEvent(str, Enum):
    CHANGE_SPECIFIC_COLUMN_VALUE = "change_specific_column_value"
    CHANGE_COLUMN_VALUE = "change_column_value"
    CHANGE_STATUS_COLUMN_VALUE = "change_status_column_value"
    CREATE_ITEM = "create_item"
    ARCHIVE_ITEM = "item_archived"
    DELETE_ITEM = "item_deleted"
    UNDELETE_ITEM = "item_restored"
    EVERY_X_HOURS = "every_x_hours"
    SNOWFLAKE_TO_MONDAY = "run_sync_snowflake_to_monday_trigger"
    SNOWFLAKE_TO_MONDAY_FILTERED = "run_sync_snowflake_to_monday_filtered_trigger"


class FeatureType(str, Enum):
    UPDATE_COLUMN_VALUE = "update_column_value"
    CREATE_PULSE = "create_pulse"
    ARCHIVE_PULSE = "archive_pulse"
    DELETE_PULSE = "delete_pulse"


class Feature(AsyncModel):
    __collection__ = "features"
    name: Optional[str] = None
    integration_id: Optional[str] = None
    external_id: Optional[str] = None
    version: Optional[str] = None
    feature_group_id: Optional[str] = None
    event: Optional[FeatureEvent] = None
    type: Optional[FeatureType] = None
