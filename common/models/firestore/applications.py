from typing import Optional, List, Any

from firedantic import Model
from pydantic import BaseModel


class FieldItem(BaseModel):
    key: str
    value: Any


class FieldInput(BaseModel):
    name: str
    description: Optional[str] = None
    label: str
    dependent_on_field: Optional[str] = None
    dependent_on_field_value: Optional[Any] = None
    type: str
    conditionally_display_on_field: Optional[str] = None
    conditionally_display_on_field_value: Optional[Any] = None
    hide_text: bool
    items: Optional[List[FieldItem]] = []
    visible: bool
    required: bool


class Application(Model):
    __collection__ = 'apps'
    name: str
    label: str
    icon: Optional[str] = None
    required_inputs: Optional[List[FieldInput]] = []
    integration_id: Optional[str] = None

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
