from typing import List, Optional

from firedantic import AsyncModel

from common.models.firestore.prices import Price


class Product(AsyncModel):
    __collection__ = "products"
    name: Optional[str] = None
    category: Optional[str] = None
    integration_name: Optional[str] = None
    description: Optional[str] = None
    stripe_id: Optional[str] = None
    hs_product_id: Optional[str] = None
    allow_trial: Optional[bool] = False
    stripe_object: Optional[dict] = None
    feature_group_ids: Optional[List[str]] = None
    prices: Optional[List[Price]] = None
    monday_plan_id: Optional[str] = None
