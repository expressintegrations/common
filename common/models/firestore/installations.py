from datetime import datetime
from typing import Optional, List

from firedantic import Model
from pydantic import BaseModel


class Output(BaseModel):
    name: str
    url: str


class Installation(Model):
    __collection__ = 'installations'
    integration_name: Optional[str] = None
    account_identifier: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    installed_by_id: Optional[str] = None
    subscription_id: Optional[str] = None
    hs_deal_id: Optional[str] = None
    price_id: Optional[str] = None
    attempted_feature_id: Optional[str] = None
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
