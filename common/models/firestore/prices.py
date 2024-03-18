from typing import Optional

from firedantic import Model


class Price(Model):
    __collection__ = 'prices'
    name: str
    product_id: str
    stripe_id: Optional[str] = None
    stripe_object: Optional[dict] = None

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

