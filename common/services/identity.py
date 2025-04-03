from common.models.firestore.connections import Authorization
from common.models.intakeq.practitioners import Role
from common.models.oauth.identity import Identity
from common.services.base import BaseService
from common.services.hubspot import HubSpotService
from common.services.intakeq import IntakeQService
from common.services.monday import MondayService
from common.services.northtext import NorthTextService


class IdentityService(BaseService):
    def __init__(self) -> None:
        super().__init__(log_name="identity.service")

    def hubspot_northtext(self, authorization: Authorization) -> Identity:
        return self.get_hubspot_identity_from_token(
            access_token=authorization.access_token
        )

    def northtext(self, authorization: Authorization) -> Identity:
        return self.get_northtext_identity_from_token(api_key=authorization.api_key)

    def express_integrations(self, authorization: Authorization) -> Identity:
        return self.get_hubspot_identity_from_token(
            access_token=authorization.access_token
        )

    def hubspot_intakeq(self, authorization: Authorization) -> Identity:
        return self.get_hubspot_identity_from_token(
            access_token=authorization.access_token
        )

    def intakeq(self, authorization: Authorization) -> Identity:
        return self.get_intakeq_identity_from_token(api_key=authorization.api_key)

    def monday_snowflake(self, authorization: Authorization) -> Identity:
        return self.get_monday_snowflake_identity_from_token(
            access_token=authorization.access_token
        )

    @staticmethod
    def get_monday_snowflake_identity_from_token(access_token: str) -> Identity:
        monday_service = MondayService(access_token=access_token)
        account_response = monday_service.get_account()
        self_response = monday_service.get_self()
        name_parts = self_response.name.split(" ")
        return Identity(
            email=self_response.email,
            first_name=name_parts[0],
            last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
            user_id=str(self_response.id),
            account_id=str(account_response.id),
            account_name=account_response.name,
        )

    @staticmethod
    def get_northtext_identity_from_token(api_key: str) -> Identity:
        northtext_service = NorthTextService(api_key=api_key)
        account_response = northtext_service.get_self()
        return Identity(
            email=account_response.result.email,
            first_name=account_response.result.first_name,
            last_name=account_response.result.last_name,
            account_id=account_response.result.id,
            account_name=account_response.result.company,
        )

    @staticmethod
    def get_intakeq_identity_from_token(api_key: str) -> Identity:
        intakeq_service = IntakeQService(api_key=api_key)
        practitioners = intakeq_service.get_practitioners()
        for practitioner in practitioners:
            if practitioner.role_name == Role.ADMINISTRATOR:
                return Identity(
                    email=practitioner.email,
                    first_name=practitioner.first_name,
                    last_name=practitioner.last_name,
                    account_id=practitioner.id,
                )

    @staticmethod
    def get_hubspot_identity_from_token(access_token: str) -> Identity:
        hubspot_service = HubSpotService(access_token=access_token)
        token_details = hubspot_service.get_token_details()
        user = hubspot_service.get_authed_user()
        return Identity(
            email=token_details.user,
            first_name=user.first_name,
            last_name=user.last_name,
            user_id=str(token_details.user_id),
            account_id=str(token_details.hub_id),
            account_name=token_details.hub_domain,
        )
