from datetime import datetime
from typing import Optional, List

from firedantic import SubModel, SubCollection
from pydantic import BaseModel


class Output(BaseModel):
    name: str
    url: str


class Installation(SubModel):
    integration_name: Optional[str] = None
    account_identifier: Optional[str] = None
    anvil_account_id: Optional[str] = None
    account_name: Optional[str] = None
    anvil_installed_by_id: Optional[str] = None
    anvil_subscription_id: Optional[str] = None
    hs_deal_id: Optional[str] = None
    active: Optional[bool] = False
    installation_in_progress: Optional[bool] = False
    installed_at: Optional[datetime] = None
    created_at: Optional[datetime] = datetime.now()
    uninstalled_at: Optional[datetime] = None
    uninstallation_in_progress: Optional[bool] = False
    activated_at: Optional[datetime] = None
    back_to_url: Optional[str] = None
    step_completed: Optional[int] = 0
    final_output: Optional[List[Output]] = None

    class Collection(SubCollection):
        __collection_tpl__ = 'integrations/{id}/installations'

    def save(self, by_alias: bool = True, exclude_unset: bool = True, exclude_none: bool = False) -> None:
        """
        Saves this model in the database.

        :raise DocumentIDError: If the document ID is not valid.
        """
        data = self.model_dump(by_alias=by_alias, exclude_unset=exclude_unset, exclude_none=exclude_none)
        if self.__document_id__ in data:
            del data[self.__document_id__]

        doc_ref = self._get_doc_ref()
        doc_ref.set(data)
        setattr(self, self.__document_id__, doc_ref.id)