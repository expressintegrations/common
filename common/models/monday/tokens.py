from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from common.models.monday.app_events import Subscription


class SessionData(BaseModel):
    client_id: str
    account_id: int
    user_id: int
    slug: str
    app_id: int
    app_version_id: int
    install_id: int
    is_admin: bool
    is_view_only: bool
    is_guest: bool
    user_kind: str | None = None
    subscription: Subscription | None = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class SessionToken(BaseModel):
    exp: int
    dat: SessionData


class AuthToken(BaseModel):
    account_id: int
    user_id: int
    board_id: Optional[int] = None
    aud: str
    exp: int
    short_lived_token: str
    iat: int
    recipe_id: Optional[int] = None
    integration_id: Optional[int] = None
    back_to_url: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel
