from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from common.models.firestore.multi_model import (
    MultiLevelAsyncSubCollection,
    MultiLevelAsyncSubModel,
)


class AuthMethod(str, Enum):
    OAUTH = "OAuth 2.0"
    API_KEY = "API Key"
    USERNAME_PASSWORD = "Username/Password"
    PRIVATE_KEY = "Private Key"


class Authorization(BaseModel):
    authentication_method: Optional[AuthMethod] = None

    # API Key
    api_key: Optional[str] = None

    # Snowflake
    account_identifier: Optional[str] = None
    region: Optional[str] = None
    cloud_platform: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    warehouse: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    password: Optional[str] = None
    passcode: Optional[str] = None
    passcode_in_password: bool = False
    private_key_file: Optional[str] = None
    private_key_file_pwd: Optional[str] = None

    # OAuth
    access_token: Optional[str] = None
    expires_in: Optional[int] = 0
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_at: Optional[int] = (
        int(datetime.now(tz=timezone.utc).timestamp()) + expires_in
    )
    id_token: Optional[str] = None

    # HubSpot
    private_token: Optional[bool] = None


class Connection(MultiLevelAsyncSubModel):
    account_identifier: Optional[str] = None
    account_id: Optional[str] = None
    authorized_by_id: Optional[str] = None
    app_name: Optional[str] = None
    authorization: Optional[Authorization] = None
    connected: Optional[bool] = False
    connected_at: Optional[datetime] = None
    connection_error: Optional[str] = None
    created_at: Optional[datetime] = datetime.now(tz=timezone.utc)
    ever_connected: Optional[bool] = False

    class Collection(MultiLevelAsyncSubCollection):
        __collection_tpl__ = "installations/{installation_id}/connections"
