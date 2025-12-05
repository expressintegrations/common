from enum import StrEnum
from typing import Optional

from firedantic import AsyncModel
from pydantic import BaseModel

from common.models.firestore.accounts import Account
from common.models.monday.monday_integrations import MondayIntegration


class MondayAccountConnection(BaseModel):
    installation_id: str
    connection_id: str
    app_name: str
    authorized_by_id: str
    user_account_identifier: str
    connected: bool
    icon: str


class Status(StrEnum):
    """Enum for status values."""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class AlertType(StrEnum):
    WARNING = "warning"
    DARK = "dark"
    ERROR = "error"
    INFO = "info"


class IntegrationAlert(AsyncModel):
    __collection__ = "monday_integration_alerts"
    account_id: int
    type: AlertType
    text: str
    link: Optional[str] = None
    link_text: Optional[str] = None
    dismissed: Optional[bool] = False


class MondayAccount(Account):
    send_success_alerts: bool = False
    send_failure_alerts: bool = True
    send_warning_alerts: bool = True
    additional_emails: Optional[list[str]] = []


class MondayAccountSettings(BaseModel):
    installation_id: str
    account_id: int
    account_slug: str
    user_id: int
    installation_url: str
    connections: list[MondayAccountConnection]
    recipes: list[MondayIntegration]
    alerts: list[IntegrationAlert]
    send_success_alerts: bool = False
    send_failure_alerts: bool = True
    send_warning_alerts: bool = True
    additional_emails: Optional[list[str]] = []
