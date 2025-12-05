from typing import Optional

from firedantic import AsyncModel


class FeatureGroup(AsyncModel):
    __collection__ = "feature_groups"
    name: Optional[str] = None
    integration_id: Optional[str] = None
