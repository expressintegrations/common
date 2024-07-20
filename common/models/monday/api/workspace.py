from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Kind(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class Workspace(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    kind: Optional[Kind] = None
    description: Optional[str] = None
