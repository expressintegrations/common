from pydantic import BaseModel


class Data(BaseModel):
    access_token: str
    access_token_expire_in: int
    refresh_token: str
    refresh_token_expire_in: int
    open_id: str
    seller_name: str
    seller_base_region: str
    user_type: int


class Authorization(BaseModel):
    code: int
    message: str
    data: Data
    request_id: str
