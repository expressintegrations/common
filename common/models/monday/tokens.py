from pydantic import BaseModel
from pydantic.alias_generators import to_camel


class AuthToken(BaseModel):
    account_id: int
    user_id: int
    aud: str
    exp: int
    short_lived_token: str
    iat: int

    class Config:
        populate_by_name = True
        alias_generator = to_camel
