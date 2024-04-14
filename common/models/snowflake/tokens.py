from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: Optional[str] = None
    expires_in: int = 0
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_at: int = int(datetime.now().timestamp()) + expires_in
    username: Optional[str] = None


class Connection(BaseModel):
    account_identifier: Optional[str] = None
    account_url: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    warehouse: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token: Optional[Token] = None
    password: Optional[str] = None
