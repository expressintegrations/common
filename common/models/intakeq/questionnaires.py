from enum import Enum
from typing import Optional, List

from pydantic import BaseModel
from pydantic.alias_generators import to_pascal


class Status(str, Enum):
    SENT = "Sent"
    PARTIAL = "Partial"
    COMPLETED = "Completed"
    OFFLINE = "Offline"


class ConsentForm(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    document_type: Optional[str] = None
    signed: Optional[bool] = None
    date_submitted: Optional[int] = None


class Intake(BaseModel):
    id: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_id: Optional[int] = None
    status: Optional[Status] = None
    date_created: Optional[int] = None
    date_submitted: Optional[int] = None
    questionnaire_name: Optional[str] = None
    questionnaire_id: Optional[str] = None
    practitioner: Optional[str] = None
    practitioner_name: Optional[str] = None
    external_client_id: Optional[str] = None
    consent_forms: Optional[List[ConsentForm]] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class Questionnaire(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    archived: Optional[bool] = None
    anonymous: Optional[bool] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class SendQuestionnaireRequest(BaseModel):
    questionnaire_id: Optional[str] = None
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    practitioner_id: Optional[str] = None
    external_client_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class DeliveryMethod(str, Enum):
    SMS = "sms"
    EMAIL = "email"


class ResendIntakeRequest(BaseModel):
    intake_id: Optional[str] = None
    delivery_method: Optional[DeliveryMethod] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal


class EventType(str, Enum):
    INTAKE_SUBMITTED = "Intake Submitted"


class IntakeWebhook(BaseModel):
    intake_id: str
    type: Optional[EventType] = None
    client_id: int
    external_practice_id: Optional[str] = None
    external_client_id: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_pascal
