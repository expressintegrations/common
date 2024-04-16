from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, field_serializer
from pydantic.alias_generators import to_pascal

from common.models.intakeq.practitioners import Practitioner


class Status(str, Enum):
    CONFIRMED = "Confirmed"
    WAITING_CONFIRMATION = "WaitingConfirmation"
    DECLINED = "Declined"
    CANCELED = "Canceled"
    MISSED = "Missed"


class TelehealthInfo(BaseModel):
    id: Optional[str] = None
    start_url: Optional[str] = None
    invitation: Optional[str] = None
    provider: Optional[str] = None
    invitation_code: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Procedure(BaseModel):
    procedure_code: Optional[str] = None
    price: Optional[int] = None
    units: Optional[int] = None
    modifiers: Optional[List[str]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class AdditionalClient(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    intake_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Appointment(BaseModel):
    id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_date_of_birth: Optional[str] = None
    client_id: Optional[int] = None
    status: Optional[Status] = None
    start_date: Optional[int] = None
    end_date: Optional[int] = None
    duration: Optional[int] = None
    service_name: Optional[str] = None
    service_id: Optional[str] = None
    location_name: Optional[str] = None
    location_id: Optional[int] = None
    price: Optional[float] = None
    practitioner_email: Optional[str] = None
    practitioner_name: Optional[str] = None
    practitioner_id: Optional[str] = None
    date_created: Optional[int] = None
    intake_id: Optional[str] = None
    booked_by_client: Optional[bool] = None
    created_by: Optional[str] = None
    appointment_package_id: Optional[str] = None
    appointment_package_name: Optional[str] = None
    telehealth_info: Optional[TelehealthInfo] = None
    procedures: Optional[List[Procedure]] = None
    additional_clients: Optional[List[AdditionalClient]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class ReminderType(str, Enum):
    SMS = "Sms"
    EMAIL = "Email"
    VOICE = "Voice"
    OPT_OUT = "OptOut"


class CreateAppointmentRequest(BaseModel):
    practitioner_id: Optional[str] = None
    client_id: Optional[int] = None
    service_id: Optional[str] = None
    location_id: Optional[int] = None
    status: Optional[Status] = None
    utc_date_time: Optional[datetime] = None
    send_client_email_notification: Optional[bool] = None
    reminder_type: Optional[ReminderType] = None

    @field_serializer('utc_date_time')
    def serialize_dt(self, dt: datetime, _info):
        return dt.timestamp() * 1000

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class UpdateAppointmentRequest(BaseModel):
    appointment_id: Optional[str] = None
    service_id: Optional[str] = None
    location_id: Optional[int] = None
    status: Optional[Status] = None
    utc_date_time: Optional[datetime] = None
    send_client_email_notification: Optional[bool] = None
    reminder_type: Optional[ReminderType] = None

    @field_serializer('utc_date_time')
    def serialize_dt(self, dt: datetime, _info):
        return dt.timestamp() * 1000

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class CancelAppointmentRequest(BaseModel):
    appointment_id: Optional[str] = None
    reason: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class EventType(str, Enum):
    APPOINTMENT_CREATED = "AppointmentCreated"
    APPOINTMENT_CONFIRMED = "AppointmentConfirmed"
    APPOINTMENT_RESCHEDULED = "AppointmentRescheduled"
    APPOINTMENT_CANCELED = "AppointmentCanceled"
    APPOINTMENT_DECLINED = "AppointmentDeclined"
    APPOINTMENT_MISSED = "AppointmentMissed"
    APPOINTMENT_DELETED = "AppointmentDeleted"


class AppointmentWebhook(BaseModel):
    event_type: Optional[EventType] = None
    action_performed_by_client: Optional[bool] = None
    appointment: Appointment
    client_id: int
    practice_id: str
    external_practice_id: Optional[str] = None
    external_client_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Location(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Service(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    duration: Optional[int] = None
    price: Optional[float] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class AppointmentSettings(BaseModel):
    locations: Optional[List[Location]] = None
    services: Optional[List[Service]] = None
    practitioners: Optional[List[Practitioner]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal
