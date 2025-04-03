from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class FileOptions(BaseModel):
    access: str
    ttl: Optional[str] = None
    overwrite: Optional[bool] = None
    duplicate_validation_strategy: Optional[str] = None
    duplicate_validation_scope: Optional[str] = None


class File(BaseModel):
    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    parent_folder_id: str | None = None
    name: str | None = None
    path: str | None = None
    size: int | None = None
    encoding: str | None = None
    type: str | None = None
    extension: str | None = None
    default_hosting_url: str | None = None
    url: str | None = None
    is_usable_in_content: bool | None = None
    access: str | None = None
    file_md5: str | None = None
    source_group: str | None = None
    archived: bool | None = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel
