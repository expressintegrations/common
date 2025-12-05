from typing import Optional

from firedantic import AsyncModel


class User(AsyncModel):
    __collection__ = "users"
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_id: Optional[str] = None
    hs_contact_id: Optional[str] = None
    anvil_user_id: Optional[str] = None
    monday_user_id: Optional[int] = None
    monday_account_id: Optional[int] = None
