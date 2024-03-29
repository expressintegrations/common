from common.models.oauth.identity import Identity
from common.services.base import BaseService
from common.services.hubspot import HubSpotService
from common.services.northtext import NorthTextService


class IdentityService(BaseService):
    def __init__(self) -> None:
        super().__init__(log_name='identity.service')

    def hubspot_northtext(self, token: str) -> Identity:
        return self.get_hubspot_identity_from_token(token=token)

    def express_integrations(self, token: str) -> Identity:
        return self.get_hubspot_identity_from_token(token=token)

    def northtext(self, token: str) -> Identity:
        return self.get_northtext_identity_from_token(token=token)

    @staticmethod
    def get_northtext_identity_from_token(token: str) -> Identity:
        northtext_service = NorthTextService(
            access_token=token
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
    def get_hubspot_identity_from_token(token: str) -> Identity:
        hubspot_service = HubSpotService(
            access_token=token
        )
        token_details = hubspot_service.get_token_details()
        user = hubspot_service.get_authed_user()
        return Identity(
            **{
                'email': token_details.user,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_id': str(token_details.user_id),
                'account_id': str(token_details.hub_id),
                'account_name': token_details.hub_domain
            }
        )
