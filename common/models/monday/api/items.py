from typing import Optional, Any

from pydantic import BaseModel


class ColumnDetails(BaseModel):
    title: str
    settings_str: Optional[str] = None


class ColumnValue(BaseModel):
    id: str
    column: Optional[ColumnDetails] = None
    type: Optional[str] = None
    value: Optional[Any] = None
    text: Optional[str] = None
