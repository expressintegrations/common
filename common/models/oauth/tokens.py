from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: Optional[str] = None
    expires_in: int = 0
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    id_token: Optional[str] = None
    private_token: Optional[str] = None
    expires_at: int = int(datetime.now().timestamp()) + expires_in


class AccountToken(BaseModel):
    id: str
    token: Token
