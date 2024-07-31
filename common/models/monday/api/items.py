from typing import Optional, Any

from pydantic import BaseModel


class SimpleColumn(BaseModel):
    id: str
    title: str


class ColumnValue(BaseModel):
    id: Optional[str] = None
    column: Optional[SimpleColumn] = None
    type: Optional[str] = None
    value: Optional[Any] = None
    text: Optional[str] = None
