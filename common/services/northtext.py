import time
from datetime import datetime
from typing import List

import requests

from common.models.northtext.account import AccountResponse
from common.models.northtext.contacts import ContactsResponse, ContactCreateRequest, Contact, ContactResponse
from common.models.northtext.errors import ErrorResponse
from common.models.northtext.messages import (
    MessagesResponse, MessageSendRequest, Message, MessageResponse,
    BulkMessagesResponse
)
from common.models.northtext.users import UsersResponse
from common.models.northtext.webhooks import WebhookCreateRequest, WebhookDeleteResponse, WebhookResponse
from common.services.base import BaseService


class NotEnoughFundsException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message


class NorthTextService(BaseService):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    base_url = 'https://api.northtext.com'

    def __init__(
        self,
        access_token: str = None
    ) -> None:
        if access_token:
            self.headers['X-API-Key'] = access_token
        else:
            raise Exception('An access token must be provided')
        super().__init__(log_name='northtext.service')

    def api_call(self, method: str, endpoint: str, data: str = None, json: [dict | list] = None) -> dict:
        r = getattr(requests, method.lower())(
            url=f"{self.base_url}/{endpoint.strip('/')}",
            data=data,
            json=json,
            headers=self.headers
        )
        # rate limiting
        while r.status_code == 429:
            time.sleep(1)
            r = getattr(requests, method.lower())(
                url=f"{self.base_url}/{endpoint.strip('/')}",
                data=data,
                json=json,
                headers=self.headers
            )
        if r.status_code >= 400:
            error_response = ErrorResponse.model_validate(r.json())
            if error_response.description == 'Not enough available balance.':
                raise NotEnoughFundsException(
                    message="Your account does not have enough funds to send the requested messages."
                )
            raise Exception(f"Error {r.status_code} {r.text}")
        return r.json()

    def get_self(self) -> AccountResponse:
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/account"
        )
        return AccountResponse.model_validate(response)

    def get_users(self) -> UsersResponse:
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/user"
        )
        return UsersResponse.model_validate(response)

    def get_message(self, message_id: int) -> MessageResponse:
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/message/{message_id}"
        )
        return MessageResponse.model_validate(response)

    def get_messages(
        self,
        limit: int = 100,
        page: int = 0,
        order: str = 'ASC',
        contact_id: int = None,
        tag_name: str = None,
        tag_value: str = None
    ) -> MessagesResponse:
        contact_param = f"&Contact={contact_id}" if contact_id else ''
        tag_name_param = f"&TagName={tag_name}" if tag_name else ''
        tag_value_param = f"&TagValue={tag_value}" if tag_value else ''
        response = self.api_call(
            'get',
            f"/api/v2/message?Limit={limit}&Page={page}&Order={order}{contact_param}{tag_name_param}{tag_value_param}"
        )
        return MessagesResponse.model_validate(response)

    def get_all_messages_by_tag(
        self,
        tag_name: str,
        tag_value: str
    ) -> List[Message]:
        page = 0
        messages_response = self.get_messages(tag_name=tag_name, tag_value=tag_value)
        messages = messages_response.result
        while len(messages_response.result) == 100:
            page += 1
            messages_response = self.get_messages(page=page, tag_name=tag_name, tag_value=tag_value)
            messages += messages_response.result

        return messages

    def send_message(self, message: MessageSendRequest) -> MessageResponse:
        response = self.api_call(
            method='post',
            endpoint=f"/api/v2/message",
            json=message.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return MessageResponse.model_validate(response)

    def send_messages(
        self,
        messages: List[MessageSendRequest]
    ) -> BulkMessagesResponse:
        response = self.api_call(
            method='post',
            endpoint='/api/v2/message/bulk',
            json=[m.model_dump(by_alias=True, exclude_unset=True, exclude_none=True) for m in messages]
        )
        return BulkMessagesResponse.model_validate(response)

    def get_contacts(
        self,
        limit: int = 100,
        page: int = 0,
        order: str = 'ASC',
        phone_number: str = None,
        since: str = None
    ) -> ContactsResponse:
        phone_param = f"&PhoneNumber={phone_number}" if phone_number else ''
        since_param = f"&lastUpdate={since}" if since else ''
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/contact?Limit={limit}&Page={page}&Order={order}{phone_param}{since_param}"
        )
        return ContactsResponse.model_validate(response)

    def get_all_contacts(self, since: datetime = None) -> List[Contact]:
        contacts_response = self.get_contacts(since=since)
        contacts = contacts_response.result
        page = 0
        while len(contacts_response.result) == 100:
            page += 1
            contacts_response = self.get_contacts(page=page, since=since)
            contacts += contacts_response.result
        return contacts

    def create_contact(self, contact: ContactCreateRequest) -> ContactResponse:
        response = self.api_call(
            method='post',
            endpoint=f"/api/v2/contact",
            json=contact.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return ContactResponse.model_validate(response)

    def get_contact(self, contact_id: int) -> ContactResponse:
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/contact/{contact_id}"
        )
        return ContactResponse.model_validate(response)

    def update_contact(self, contact_id: int, contact: Contact) -> ContactResponse:
        response = self.api_call(
            'put',
            f"/api/v2/contact/{contact_id}",
            json=contact.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return ContactResponse.model_validate(response)

    def create_webhook(self, webhook: WebhookCreateRequest) -> WebhookResponse:
        response = self.api_call(
            method='post',
            endpoint='/api/v2/webhook',
            json=webhook.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return WebhookResponse.model_validate(response)

    def delete_webhook(self, webhook_id: int) -> WebhookDeleteResponse:
        response = self.api_call(
            method='delete',
            endpoint=f'/api/v2/webhook/{webhook_id}'
        )
        return WebhookDeleteResponse.model_validate(response)
