from enum import Enum
from pydantic import BaseModel


class EventType(str, Enum):
    SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    SUBSCRIPTION_CREATED = "customer.subscription.created"
    SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    SUBSCRIPTION_TRIAL_WILL_END = "customer.subscription.trial_will_end"
    CHECKOUT_SESSION_COMPLETED = "checkout.session.completed"
    INVOICE_PAID = "invoice.paid"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    PRODUCT_CREATED = "product.created"
    PRODUCT_DELETED = "product.deleted"
    PRODUCT_UPDATED = "product.updated"
    PRICE_CREATED = "price.created"
    PRICE_DELETED = "price.deleted"
    PRICE_UPDATED = "price.updated"
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"


class StripeWebhookEvent(BaseModel):
    id: str
    object: str
    api_version: str
    type: EventType
    created: int
    data: dict
    livemode: bool
    pending_webhooks: int
