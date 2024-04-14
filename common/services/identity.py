from common.models.firestore.connections import Authorization
from common.models.oauth.identity import Identity
from common.services.base import BaseService
from common.services.hubspot import HubSpotService
from common.services.northtext import NorthTextService


class IdentityService(BaseService):
    def __init__(self) -> None:
        super().__init__(log_name='identity.service')

    def hubspot_northtext(self, authorization: Authorization) -> Identity:
        return self.get_hubspot_identity_from_token(access_token=authorization.access_token)

    def express_integrations(self, authorization: Authorization) -> Identity:
        return self.get_hubspot_identity_from_token(access_token=authorization.access_token)

    def northtext(self, authorization: Authorization) -> Identity:
        return self.get_northtext_identity_from_token(api_key=authorization.api_key)

    @staticmethod
    def get_northtext_identity_from_token(api_key: str) -> Identity:
        northtext_service = NorthTextService(
            api_key=api_key
        )
        account_response = northtext_service.get_self()
        return Identity(
            email=account_response.result.email,
            first_name=account_response.result.first_name,
            last_name=account_response.result.last_name,
            account_id=account_response.result.id,
            account_name=account_response.result.company
        )

    @staticmethod
    def get_hubspot_identity_from_token(access_token: str) -> Identity:
        hubspot_service = HubSpotService(
            access_token=access_token
        )
        token_details = hubspot_service.get_token_details()
        user = hubspot_service.get_authed_user()
        return Identity(
            email=token_details.user,
            first_name=user.first_name,
            last_name=user.last_name,
            user_id=str(token_details.user_id),
            account_id=str(token_details.hub_id),
            account_name=token_details.hub_domain
        )
