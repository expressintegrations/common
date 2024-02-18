import stripe

from common.services.base import BaseService


class StripeService(BaseService):
    def __init__(
        self,
        stripe_key: str
    ) -> None:
        self.stripe_client = stripe
        self.stripe_key = stripe_key
        stripe.api_key = stripe_key
        super().__init__(log_name='stripe.service')

    def get_billing_portal_configuration(self, base_url, integration):
        if integration['stripe_billing_portal_config_id']:
            return integration['stripe_billing_portal_config_id']
        features = {
            "customer_update": {
                "allowed_updates": ["name", "email", "address", "phone", "tax_id"],
                "enabled": True,
            },
            "invoice_history": {"enabled": True},
            "payment_method_update": {"enabled": True},
            "subscription_cancel": {
                "enabled": True,
                "cancellation_reason": {
                    "enabled": True,
                    "options": ["too_expensive", "missing_features", "switched_service", "unused",
                                "customer_service", "too_complex", "low_quality"]
                },
                "mode": "at_period_end"
            }
        }
        if len(
            [
                prod for prod in integration['products']
                if len(
                    [p['stripe_id'] for p in prod['prices'] if p['stripe_object']['billing_scheme'] == 'per_unit']
                ) > 0
            ]
        ) > 0:
            features["subscription_update"] = {
                "enabled": True,
                "default_allowed_updates": ["price", "promotion_code"],
                "products": [
                    {
                        "product": product['stripe_id'],
                        "prices": [
                            price['stripe_id'] for price in product['prices']
                            if price['stripe_object']['billing_scheme'] == 'per_unit'
                        ]
                    } for product in integration['products']
                    if len(
                        [
                            price['stripe_id'] for price in product['prices']
                            if price['stripe_object']['billing_scheme'] == 'per_unit'
                        ]
                    ) > 0
                ]
            }

        config = self.stripe_client.billing_portal.Configuration.create(
            features=features,
            business_profile={
                "headline": f"Manage your {integration['label']} subscription",
                "privacy_policy_url": "https://www.growth-operations.com/privacy-policy",
                "terms_of_service_url": "https://www.growth-operations.com/terms-of-service",
            },
            default_return_url=f"{base_url}/#my-integrations",
            metadata={
                "integration_id": integration.get_id()
            }
        )
        integration['stripe_billing_portal_config_id'] = config['id']
        return integration['stripe_billing_portal_config_id']

    def create_billing_session(self, customer_id: str, billing_portal_config_id: str):
        try:
            return self.stripe_client.billing_portal.Session.create(
                customer=customer_id,
                configuration=billing_portal_config_id
            )
        except Exception as e:
            print(e)
            return {'error': {'message': str(e)}}

    def create_billing_portal_configuration(self, base_url: str, features, integration_label: str, integration_id: str):
        return self.stripe_client.billing_portal.Configuration.create(
            features=features,
            business_profile={
                "headline": f"Manage your {integration_label} subscription",
                "privacy_policy_url": "https://www.growth-operations.com/privacy-policy",
                "terms_of_service_url": "https://www.growth-operations.com/terms-of-service",
            },
            default_return_url=f"{base_url}/#my-integrations",
            metadata={
                "integration_id": integration_id
            }
        )

    def get_billing_session_for_installation(self, base_url: str, installation):
        try:
            billing_portal_config_id = self.get_billing_portal_configuration(
                base_url=base_url,
                integration=installation['integration']
            )
            billing_session = stripe.billing_portal.Session.create(
                customer=installation['account']['stripe_customer_id'],
                configuration=billing_portal_config_id
            )
            return billing_session
        except Exception as e:
            print(e)
            return {'error': {'message': str(e)}}

    def get_price(self, price_id: str):
        return self.stripe_client.Price.retrieve(price_id, expand=['tiers'])

    def update_price(self, price_id: str, **kwargs):
        return self.stripe_client.Price.modify(price_id, **kwargs)

    def get_product(self, product_id: str):
        return self.stripe_client.Product.retrieve(product_id)

    def update_product(self, product_id: str, **kwargs):
        return self.stripe_client.Product.modify(product_id, **kwargs)

    def cancel_subscription(self, subscription_id: str):
        self.update_subscription(
            subscription_id=subscription_id,
            cancel_at_period_end=True
        )

    def update_subscription(self, subscription_id: str, **kwargs):
        self.stripe_client.Subscription.modify(
            subscription_id,
            **kwargs
        )

    def create_usage_record(self, subscription_item_id: str, quantity):
        return self.stripe_client.SubscriptionItem.create_usage_record(
            subscription_item_id,
            quantity=quantity,
            action='set'
        )

    def get_payment_method(self, payment_method_id: str):
        return self.stripe_client.PaymentMethod.retrieve(payment_method_id)

    def get_subscription(self, subscription_id: str):
        return self.stripe_client.Subscription.retrieve(subscription_id)
