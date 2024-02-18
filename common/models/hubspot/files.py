from typing import Optional

from pydantic import BaseModel


class FileOptions(BaseModel):
    access: str
    ttl: Optional[str] = None
    overwrite: Optional[bool] = None
    duplicate_validation_strategy: Optional[str] = None
    duplicate_validation_scope: Optional[str] = None
