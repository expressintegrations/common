from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class TimelineIFrame(BaseModel):
    link_label: str
    header_label: str
    url: str
    width: int
    height: int

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class TimelineEvent(BaseModel):
    event_template_id: int
    extra_data: Optional[dict] = None
    timeline_i_frame: Optional[TimelineIFrame] = None
    domain: Optional[str] = None
    utk: Optional[str] = None
    email: Optional[str] = None
    object_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    tokens: dict

    class Config:
        populate_by_name = True
        alias_generator = to_camel
