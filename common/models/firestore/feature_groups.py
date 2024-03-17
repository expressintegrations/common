from pydantic import BaseModel


class FeatureGroup(BaseModel):
    name: str
    integration_id: str
