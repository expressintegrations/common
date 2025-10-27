from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class SessionData(BaseModel):
    account_id: int
    user_id: int

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
