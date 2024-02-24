from typing import Optional

from pydantic import BaseModel


class InstallationRequest(BaseModel):
    connection_id: str
    user_id: str
    integration_name: str
    installation_id: Optional[str] = None
    inputs: dict
