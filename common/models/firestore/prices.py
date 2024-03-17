from typing import Optional

from pydantic import BaseModel


class Price(BaseModel):
    name: str
    product_id: str
    stripe_id: Optional[str] = None
    stripe_object: Optional[dict] = None

