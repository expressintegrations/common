from typing import Optional, List

from pydantic import BaseModel

from common.models.firestore.prices import Price


class Product(BaseModel):
    name: str
    category: Optional[str] = None
    integration_id: Optional[str] = None
    description: Optional[str] = None
    stripe_id: Optional[str] = None
    hs_product_id: Optional[str] = None
    prices: List[Price]
    allow_trial: Optional[bool] = False
    stripe_object: Optional[dict] = None
    feature_group_ids: Optional[List[str]] = None
