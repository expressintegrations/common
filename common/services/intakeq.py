import time
from datetime import datetime
from typing import List

import requests

from common.models.intakeq.appointments import (
    Status, Appointment, AppointmentSettings, CreateAppointmentRequest,
    UpdateAppointmentRequest, CancelAppointmentRequest
)
from common.models.intakeq.clients import Client, Tag, Diagnosis
from common.models.intakeq.practitioners import Practitioner
from common.models.intakeq.questionnaires import Intake, Questionnaire, ResendIntakeRequest
from common.services.base import BaseService


class IntakeQService(BaseService):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    base_url = 'https://intakeq.com/api/v1'

    def __init__(
        self,
        api_key: str = None
    ) -> None:
        if api_key:
            self.headers['X-Auth-Key'] = api_key
        else:
            raise Exception('An access token must be provided')
        super().__init__(log_name='intakeq.service')

    def api_call(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        data: str = None,
        json: [dict | list] = None
    ) -> dict:
        r = getattr(requests, method.lower())(
            url=f"{self.base_url}/{endpoint.strip('/')}",
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )
        # rate limiting
        while r.status_code == 429:
            time.sleep(1)
            r = getattr(requests, method.lower())(
                url=f"{self.base_url}/{endpoint.strip('/')}",
                params=params,
                data=data,
                json=json,
                headers=self.headers
            )
        if r.status_code >= 400:
            raise Exception(f"Error {r.status_code} {r.text}")
        return r.json()

    def get_clients(
        self,
        search: [str | int] = None,
        page: int = None,
        include_profile: bool = None,
        date_created_start: datetime = None,
        date_created_end: datetime = None,
        date_updated_start: datetime = None,
        date_updated_end: datetime = None,
        external_client_id: str = None,
        deleted_only: bool = None,
        **kwargs
    ) -> List[Client]:
        params = {
                     'search': search,
                     'page': page,
                     'includeProfile': include_profile,
                     'dateCreatedStart': date_created_start.strftime('%Y-%m-%d') if date_created_start else None,
                     'dateCreatedEnd': date_created_end.strftime('%Y-%m-%d') if date_created_end else None,
                     'dateUpdatedStart': date_updated_start.strftime('%Y-%m-%d') if date_updated_start else None,
                     'dateUpdatedEnd': date_updated_end.strftime('%Y-%m-%d') if date_updated_end else None,
                     'externalClientId': external_client_id,
                     'deletedOnly': deleted_only
                 } | kwargs
        params = {k: v for k, v in params.items() if v is not None}
        response = self.api_call(
            method='get',
            endpoint=f"clients",
            params=params
        )
        return [Client.model_validate(client) for client in response]

    def add_tag_to_client(self, tag: Tag) -> None:
        self.api_call(
            method='post',
            endpoint=f"clientTags",
            json=tag.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        )

    def remove_tag_from_client(self, client_id: int, tag: str) -> None:
        self.api_call(
            method='delete',
            endpoint=f"clientTags",
            params={'clientId': client_id, 'tag': tag}
        )

    def get_client_diagnoses(self, client_id: int) -> List[Diagnosis]:
        response = self.api_call(
            method='get',
            endpoint=f"client/{client_id}/diagnoses"
        )
        return [Diagnosis.model_validate(diagnosis) for diagnosis in response]

    def get_appointments(
        self,
        client: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        status: Status = None,
        practitioner_email: str = None,
        page: int = None,
        updated_since: datetime = None,
        deleted_only: bool = None
    ) -> List[Appointment]:
        params = {
            'client': client,
            'startDate': start_date.strftime('%Y-%m-%d') if start_date else None,
            'endDate': end_date.strftime('%Y-%m-%d') if end_date else None,
            'status': status.value,
            'practitionerEmail': practitioner_email,
            'page': page,
            'updatedSince': updated_since.strftime('%Y-%m-%d') if updated_since else None,
            'deletedOnly': deleted_only
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.api_call(
            method='get',
            endpoint=f"appointments",
            params=params
        )
        return [Appointment.model_validate(appointment) for appointment in response]

    def get_appointment(
        self,
        appointment_id: str
    ) -> Appointment:
        response = self.api_call(
            method='get',
            endpoint=f"appointments/{appointment_id}"
        )
        return Appointment.model_validate(response)

    def get_appointment_settings(self) -> AppointmentSettings:
        response = self.api_call(
            method='get',
            endpoint=f"appointments/settings"
        )
        return AppointmentSettings.model_validate(response)

    def create_appointment(
        self,
        appointment: CreateAppointmentRequest
    ) -> Appointment:
        response = self.api_call(
            method='post',
            endpoint=f"appointments",
            json=appointment.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Appointment.model_validate(response)

    def update_appointment(
        self,
        appointment: UpdateAppointmentRequest
    ) -> Appointment:
        response = self.api_call(
            method='put',
            endpoint=f"appointments",
            json=appointment.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Appointment.model_validate(response)

    def cancel_appointment(
        self,
        appointment: CancelAppointmentRequest
    ) -> Appointment:
        response = self.api_call(
            method='post',
            endpoint=f"appointments/cancellation",
            json=appointment.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Appointment.model_validate(response)

    def get_intake_forms(
        self,
        client: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        page: int = None,
        all_forms: bool = None,
        client_id: int = None,
        external_client_id: str = None,
        updated_since: datetime = None,
        deleted_only: bool = None
    ) -> List[Intake]:
        params = {
            'client': client,
            'startDate': start_date.strftime('%Y-%m-%d') if start_date else None,
            'endDate': end_date.strftime('%Y-%m-%d') if end_date else None,
            'page': page,
            'all': all_forms,
            'clientId': client_id,
            'externalClientId': external_client_id,
            'updatedSince': updated_since.strftime('%Y-%m-%d') if updated_since else None,
            'deletedOnly': deleted_only
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = self.api_call(
            method='get',
            endpoint=f"intakes/summary",
            params=params
        )
        return [Intake.model_validate(intake) for intake in response]

    def get_intake(
        self,
        intake_id: str
    ) -> Intake:
        response = self.api_call(
            method='get',
            endpoint=f"intakes/{intake_id}"
        )
        return Intake.model_validate(response)

    def get_questionnaires(
        self
    ) -> List[Questionnaire]:
        response = self.api_call(
            method='get',
            endpoint=f"questionnaires"
        )
        return [Questionnaire.model_validate(questionnaire) for questionnaire in response]

    def get_practitioners(
        self
    ) -> List[Practitioner]:
        response = self.api_call(
            method='get',
            endpoint=f"practitioners"
        )
        return [Practitioner.model_validate(practitioner) for practitioner in response]

    def send_questionnaire(
        self,
        questionnaire: Questionnaire
    ) -> Intake:
        response = self.api_call(
            method='post',
            endpoint=f"intakes/send",
            json=questionnaire.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Intake.model_validate(response)

    def resend_questionnaire(
        self,
        resend_intake_request: ResendIntakeRequest
    ) -> Intake:
        response = self.api_call(
            method='post',
            endpoint=f"intakes/resend",
            json=resend_intake_request.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Intake.model_validate(response)
