import base64
from datetime import datetime, timezone
from typing import Any

import anvil.server
from anvil.tables import app_tables

from common.services.base import BaseService


class AnvilService(BaseService):
    def __init__(self, anvil_uplink_key: str) -> None:
        self.anvil_uplink_key = anvil_uplink_key
        self.connected = False
        super().__init__(
            log_name="firestore.service",
            exclude_inputs=["set_account_connection"],
            exclude_outputs=["get_account_connection"],
        )

    def connect(self):
        anvil.server.connect(self.anvil_uplink_key)
        self.connected = True

    def disconnect(self):
        anvil.server.disconnect()
        self.connected = False

    def list_app_settings_by_portal_id(
        self, app_name: str, portal_id: int, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        account_settings = app_tables.app_settings.search(
            app_name=app_name, portal_id=portal_id
        )
        if not keep_alive:
            self.disconnect()
        return account_settings

    def create_app_settings(
        self, app_name: str, portal_id: int, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        app_setting = app_tables.app_settings.add_row(
            app_name=app_name, portal_id=portal_id
        )
        if not keep_alive:
            self.disconnect()
        return app_setting

    def get_file_attachment_by_id(
        self, file_attachment_id: str, decode: bool = True, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        file_attachment_id = (
            base64.b64decode(file_attachment_id).decode("UTF-8")
            if decode
            else file_attachment_id
        )
        file_attachment = app_tables.file_attachments.get_by_id(
            base64.b64decode(file_attachment_id).decode("UTF-8")
        )
        if not keep_alive:
            self.disconnect()
        return file_attachment

    def get_installation_by_id(
        self, installation_id: str, decode: bool = True, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        installation_id = (
            base64.b64decode(installation_id).decode("UTF-8")
            if decode
            else installation_id
        )
        installation = app_tables.installations.get_by_id(installation_id)
        if not keep_alive:
            self.disconnect()
        return installation

    def get_active_installation_for_integration(
        self, integration, portal_id: str, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        installation = app_tables.installations.get(
            integration=integration,
            active=True,
            uninstalled_at=None,
            uninstallation_in_progress=False,
            account_identifier=portal_id,
        )
        if not keep_alive:
            self.disconnect()
        return installation

    def get_installations_by_account_identifier(
        self, portal_id, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        installations = app_tables.installations.search(
            account_identifier=f"{portal_id}"
        )
        if not keep_alive:
            self.disconnect()
        return installations

    def get_installations_by_account(self, account, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        installations = app_tables.installations.search(account=account)
        if not keep_alive:
            self.disconnect()
        return installations

    def get_connection_by_id(
        self, connection_id: str, decode: bool = True, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        connection_id = (
            base64.b64decode(connection_id).decode("UTF-8") if decode else connection_id
        )
        connection = app_tables.connections.get_by_id(connection_id)
        if not keep_alive:
            self.disconnect()
        return connection

    def get_account_by_id(self, account_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        account = app_tables.accounts.get_by_id(account_id)
        if not keep_alive:
            self.disconnect()
        return account

    def get_account_by_identifier(self, identifier: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        account = app_tables.accounts.get(account_identifier=str(identifier))
        if not keep_alive:
            self.disconnect()
        return account

    def get_account_by_stripe_customer_id(
        self, customer_id: str, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        account = app_tables.accounts.get(stripe_customer_id=customer_id)
        if not keep_alive:
            self.disconnect()
        return account

    def create_account(
        self, account_id: Any, name: str, application_name: str, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        account = app_tables.accounts.add_row(
            account_identifier=str(account_id),
            name=name,
            active=True,
            created_at=datetime.now(tz=timezone.utc),
            source={"application": application_name},
        )
        if not keep_alive:
            self.disconnect()
        return account

    def get_user_by_id(self, user_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        user = app_tables.users.get_by_id(user_id)
        if not keep_alive:
            self.disconnect()
        return user

    def get_subscription_by_checkout_session_id(
        self, session_id: str, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        subscription = app_tables.subscriptions.get(checkout_session_id=session_id)
        if not keep_alive:
            self.disconnect()
        return subscription

    def get_subscription_by_stripe_id(
        self, subscription_id: str, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        subscription = app_tables.subscriptions.get(stripe_id=subscription_id)
        if not keep_alive:
            self.disconnect()
        return subscription

    def get_products_by_stripe_id(self, stripe_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        products = app_tables.products.search(stripe_id=stripe_id)
        if not keep_alive:
            self.disconnect()
        return products

    def delete_products_by_stripe_id(self, product_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        for product in app_tables.products.search(stripe_id=product_id):
            for price in product["prices"]:
                price.delete()
            product.delete()
        if not keep_alive:
            self.disconnect_from_anvil()

    def delete_price_by_stripe_id(self, price_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        for price in app_tables.prices.search(stripe_id=price_id):
            product = price["product"]
            price.delete()
            product.update(prices=app_tables.prices.search(product=product))
        if not keep_alive:
            self.disconnect_from_anvil()

    def update_subscription_with_checkout_session(
        self, session, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        subscription = app_tables.subscriptions.get(checkout_session_id=session["id"])
        if not subscription:
            self.logger.log_text(
                f"No subscription for checkout session {session['id']}",
                severity="DEBUG",
            )
            if not keep_alive:
                self.disconnect_from_anvil()
            return
        subscription["installation"]["account"]["stripe_customer_id"] = session[
            "customer"
        ]
        subscription["stripe_id"] = session["subscription"]
        subscription["installation"]["account"]["stripe_customer_id"] = session[
            "customer"
        ]
        subscription["stripe_id"] = session["subscription"]
        if not keep_alive:
            self.disconnect_from_anvil()

    def update_anvil_product_from_stripe_product(
        self, stripe_product, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        product = app_tables.products.get(stripe_id=stripe_product["id"])
        if not product:
            product = app_tables.products.add_row(
                name=stripe_product["name"],
                category=stripe_product["metadata"].get("category"),
                description=f"<p>{stripe_product['description']}</p>",
                stripe_id=stripe_product["id"],
                stripe_object=stripe_product,
            )
        else:
            category = stripe_product["metadata"].get("category")
            product.update(
                name=stripe_product["name"],
                category=category if category else product["category"],
                stripe_object=stripe_product,
            )
        for integration in app_tables.integrations.search(label=product["name"]):
            product.update(integration=integration)

        prices = app_tables.prices.search(product=product)
        product.update(prices=list(prices))
        if not keep_alive:
            self.disconnect_from_anvil()
        return product

    def update_anvil_price_from_stripe_price(
        self, stripe_price, stripe_product, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        price = app_tables.prices.get(stripe_id=stripe_price["id"])
        name = f"{stripe_product['name']}"
        if stripe_price["type"] == "recurring":
            name = f"{name} {stripe_price['recurring']['interval']}ly"
        product = self.update_anvil_product_from_stripe_product(
            stripe_product=stripe_product
        )
        if not price:
            price = app_tables.prices.add_row(
                name=name,
                product=product,
                stripe_id=stripe_price["id"],
                stripe_object=stripe_price,
            )
            prices = list(product["prices"]) if product["prices"] else []
            prices.append(price)
            product.update(prices=prices)
        else:
            price.update(name=name, stripe_object=stripe_price)
        if not keep_alive:
            self.disconnect_from_anvil()
        return price

    def update_subscription_from_stripe_subscription(
        self, stripe_sub, keep_alive: bool = True
    ):
        if not self.connected:
            self.connect()
        subscription = app_tables.subscriptions.get(stripe_id=stripe_sub["id"])
        if not subscription and "anvil_subscription" in stripe_sub["metadata"]:
            subscription = app_tables.subscriptions.get_by_id(
                stripe_sub["metadata"]["anvil_subscription"]
            )
        if not subscription:
            print(f"No anvil subscription found with id: {stripe_sub['id']}")
            if not keep_alive:
                self.disconnect_from_anvil()
            return

        prices = []
        for item in stripe_sub["items"]["data"]:
            prices.append(app_tables.prices.get(stripe_id=item["price"]["id"]))
        ended_at = (
            datetime.fromtimestamp(stripe_sub["ended_at"])
            if stripe_sub["ended_at"]
            else None
        )
        subscription.update(
            active=stripe_sub["status"] in ["active", "trialing"],
            prices=prices,
            is_trial=stripe_sub["status"] == "trialing",
            cancel_at_period_end=stripe_sub["cancel_at_period_end"],
            ended_at=ended_at,
            stripe_object=stripe_sub,
        )
        if stripe_sub["status"] not in ["active", "trialing"]:
            subscription["installation"].update(active=False)
        if not keep_alive:
            self.disconnect_from_anvil()
        return subscription

    def cancel_subscription(self, subscription, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        subscription["cancel_at_period_end"] = True
        if not keep_alive:
            self.disconnect_from_anvil()

    def get_integration_by_app_name(self, app_name: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        integration = app_tables.integrations.get(name=app_name)
        if not keep_alive:
            self.disconnect_from_anvil()
        return integration

    def get_feature_by_external_id(self, external_id: str, keep_alive: bool = True):
        if not self.connected:
            self.connect()
        feature = app_tables.features.get(external_id=external_id)
        if not keep_alive:
            self.disconnect_from_anvil()
        return feature
