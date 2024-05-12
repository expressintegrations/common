from typing import Optional, List, Any, Dict

from firedantic import Model
from pydantic import BaseModel


class DependentField(BaseModel):
    label: str
    value: str


class FieldItem(BaseModel):
    key: str
    value: Any


class FieldInput(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    label: Optional[str] = None
    dependent_field_values: Optional[Dict[str, List[DependentField]]] = None
    dependent_on_field: Optional[str] = None
    dependent_on_field_value: Optional[Any] = None
    type: Optional[str] = None
    conditionally_display_on_field: Optional[str] = None
    conditionally_display_on_field_value: Optional[Any] = None
    hide_text: Optional[bool] = None
    items: Optional[List[FieldItem]] = []
    visible: Optional[bool] = None
    required: Optional[bool] = None


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
