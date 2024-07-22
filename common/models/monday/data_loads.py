from typing import List, Optional

from pydantic import BaseModel

from common.models.monday.api.boards import BoardColumn


class BoardColumnWithSnowflakeDefinition(BaseModel):
    column: Optional[BoardColumn] = None
    snowflake_name: Optional[str] = None
    snowflake_type: Optional[str] = None
    snowflake_definition: Optional[str] = None


class LoadMondayDataRequest(BaseModel):
    monday_account_id: int
    monday_user_id: int
    table_name: str
    snowflake_key_column: str
    columns_with_snowflake_definitions: List[BoardColumnWithSnowflakeDefinition]
    items: List[List[dict]]


class LoadMondayBoardActivityRequest(BaseModel):
    monday_account_id: int
    monday_user_id: int
    table_name: str
    temp_table_name: str
    board_activity: List[dict]
