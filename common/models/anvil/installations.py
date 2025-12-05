from pydantic import BaseModel


class InstallationRequest(BaseModel):
    connection_id: str
    user_id: str
    integration_name: str
    installation_id: str
    inputs: dict
