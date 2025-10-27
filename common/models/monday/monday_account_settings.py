from typing import Optional
from enum import StrEnum

from firedantic import Model
from pydantic import BaseModel
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


class IntegrationAlert(Model):
    __collection__ = "monday_integration_alerts"
    account_id: str
    type: AlertType
    text: str
    link: Optional[str] = None
    link_text: Optional[str] = None
    dismissed: Optional[bool] = False


class MondayAccountSettings(BaseModel):
    account_id: int
    user_id: int
    connections: list[MondayAccountConnection]
    recipes: list[MondayIntegration]
    alerts: list[IntegrationAlert]
