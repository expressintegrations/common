from typing import Optional, List

from firedantic import Model


class Product(Model):
    __collection__ = 'products'
    name: str
    category: Optional[str] = None
    integration_name: Optional[str] = None
    description: Optional[str] = None
    stripe_id: Optional[str] = None
    hs_product_id: Optional[str] = None
    allow_trial: Optional[bool] = False
    stripe_object: Optional[dict] = None
    feature_group_ids: Optional[List[str]] = None

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
