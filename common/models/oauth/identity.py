from pydantic import BaseModel


class Identity(BaseModel):
    email: str
    first_name: str
    last_name: str
    user_id: str
    account_id: str
    account_name: str
