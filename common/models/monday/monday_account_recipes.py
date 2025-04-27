from datetime import datetime
from typing import Optional
from enum import StrEnum

from firedantic import Model, SubModel, SubCollection
from pydantic import BaseModel


class MondayAccountConnection(BaseModel):
    installation_id: str
    connection_id: str
    app_name: str
    authorized_by_id: str
    user_account_identifier: str
    connected: bool
    icon: str


class MondayAccountRecipe(Model):
    __collection__ = "monday_account_recipes"
    account_id: int
    integration_id: int
    user_id: int
    board_id: int
    board_name: str
    recipe_id: int
    recipe_name: str
    last_success: Optional[datetime] = None


class Status(StrEnum):
    """Enum for status values."""

    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"


class IntegrationRun(SubModel):
    status: Status
    error_message: Optional[str] = None
    run_at: Optional[datetime] = None

    class Collection(SubCollection):
        __collection_tpl__ = "monday_account_recipes/{id}/integration_runs"

    def save(
        self,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_none: bool = False,
    ) -> None:
        """
        Saves this model in the database.

        :raise DocumentIDError: If the document ID is not valid.
        """
        data = self.model_dump(
            by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none
        )
        if self.__document_id__ in data:
            del data[self.__document_id__]

        doc_ref = self._get_doc_ref()
        doc_ref.set(data)
        setattr(self, self.__document_id__, doc_ref.id)


class AlertType(StrEnum):
    WARNING = "warning"
    DARK = "dark"
    ERROR = "error"
    INFO = "info"


class IntegrationAlert(Model):
    __collection__ = "monday_integration_alerts"
    type: AlertType
    text: str
    link: Optional[str] = None
    link_text: Optional[str] = None
    dismissed: Optional[bool] = False


class MondayAccountSettings(BaseModel):
    account_id: str
    user_id: str
    connections: list[MondayAccountConnection]
    recipes: list[MondayAccountRecipe]
    alerts: list[IntegrationAlert]
