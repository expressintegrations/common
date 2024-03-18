from datetime import datetime
from typing import Optional, List

from firedantic import Model


class Subscription(Model):
    __collection__ = 'subscriptions'
    account_id: Optional[str] = None
    stripe_id: Optional[str] = None
    installation_ids: Optional[List[str]] = None
    price_ids: Optional[List[str]] = None
    active: Optional[bool] = False
    is_trial: Optional[bool] = False
    created_at: datetime = datetime.now()
    ended_at: Optional[datetime] = None
    cancel_at_period_end: Optional[bool] = False
    checkout_session_id: Optional[str] = None
    stripe_object: Optional[dict] = None
    attempted_feature_id: Optional[str] = None

    def save(self, by_alias: bool = True, exclude_unset: bool = False, exclude_none: bool = False) -> None:
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
