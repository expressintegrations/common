from datetime import datetime
from typing import Optional

from firedantic import SubModel, SubCollection
from pydantic import BaseModel


class Authorization(BaseModel):
    authentication_method: str

    # API Key
    api_key: Optional[str] = None

    # Snowflake
    account_identifier: Optional[str] = None
    account_url: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    warehouse: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    password: Optional[str] = None

    # OAuth
    access_token: Optional[str] = None
    expires_in: Optional[int] = 0
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_at: Optional[int] = int(datetime.now().timestamp()) + expires_in


class Connection(SubModel):
    account_identifier: Optional[str] = None
    anvil_account_id: Optional[str] = None
    anvil_authorized_by_id: Optional[str] = None
    app_name: Optional[str] = None
    authorization: Optional[Authorization] = None
    connected: bool = False
    connected_at: Optional[datetime] = None
    connection_error: Optional[str] = None
    created_at: datetime = datetime.now()
    ever_connected: bool = False

    class Collection(SubCollection):
        __collection_tpl__ = 'integrations/{integration_name}/installations/{id}/connections'

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
