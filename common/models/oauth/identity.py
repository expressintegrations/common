from typing import Optional

from pydantic import BaseModel


class Identity(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
