from typing import Optional

from firedantic import AsyncModel


class Price(AsyncModel):
    __collection__ = "prices"
    name: Optional[str] = None
    product_id: Optional[str] = None
    stripe_id: Optional[str] = None
    stripe_object: Optional[dict] = None
    monday_billing_period: Optional[str] = None
