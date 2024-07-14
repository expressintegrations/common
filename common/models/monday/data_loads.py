from typing import List

from pydantic import BaseModel


class LoadMondayDataRequest(BaseModel):
    monday_account_id: int
    monday_user_id: int
    table_name: str
    snowflake_key_column: str
    columns_with_snowflake_definitions: List[dict]
    items: List[List[dict]]


class LoadMondayBoardActivityRequest(BaseModel):
    monday_account_id: int
    monday_user_id: int
    table_name: str
    temp_table_name: str
    board_activity: List[dict]
