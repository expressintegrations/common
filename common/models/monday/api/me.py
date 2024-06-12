from typing import List, Optional

from pydantic import BaseModel


class Account(BaseModel):
    id: str


class Team(BaseModel):
    id: str
    name: str


class Me(BaseModel):
    account: Optional[Account] = None
    birthday: Optional[str] = None
    country_code: Optional[str] = None
    created_at: Optional[str] = None
    join_date: Optional[str] = None
    email: Optional[str] = None
    enabled: Optional[bool] = None
    id: Optional[int] = None
    is_admin: Optional[bool] = None
    is_guest: Optional[bool] = None
    is_pending: Optional[bool] = None
    is_view_only: Optional[bool] = None
    location: Optional[str] = None
    mobile_phone: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    photo_original: Optional[str] = None
    photo_small: Optional[str] = None
    photo_thumb: Optional[str] = None
    photo_thumb_small: Optional[str] = None
    photo_tiny: Optional[str] = None
    teams: Optional[List[Team]] = None
    time_zone_identifier: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    utc_hours_diff: Optional[int] = None
