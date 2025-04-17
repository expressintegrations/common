from typing import Optional

from firedantic import Model


class User(Model):
    __collection__ = "users"
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    account_id: Optional[str] = None
    hs_contact_id: Optional[str] = None
    anvil_user_id: Optional[str] = None
    monday_user_id: Optional[int] = None
    monday_account_id: Optional[int] = None

    def save(
        self,
        by_alias: bool = True,
        exclude_unset: bool = True,
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
