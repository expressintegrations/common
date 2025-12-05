from typing import List, Optional

from firedantic import AsyncModel

from common.models.firestore.applications import FieldInput


class Integration(AsyncModel):
    __collection__ = "integrations"
    label: Optional[str] = None
    name: Optional[str] = None
    required_application_ids: Optional[List[str]] = []
    identity_application_id: Optional[str] = None
    external_billing: Optional[bool] = None
    default_product_id: Optional[str] = None
    one_time_product_id: Optional[str] = None
    product_ids: Optional[List[str]] = []
    required_inputs: Optional[List[FieldInput]] = []
    stripe_billing_portal_config_id: Optional[str] = None
    installable: Optional[bool] = None
    default_back_to_url: Optional[str] = None
    total_installation_steps: Optional[int] = 1
