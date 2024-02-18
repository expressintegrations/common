from datetime import datetime
from typing import List

import requests
import time

from common.models.northtext.contacts import ContactsResponse, ContactCreateRequest, Contact
from common.models.northtext.messages import (
    MessagesResponse, MessageSendRequest, Message, MessageResponse,
    BulkMessagesResponse
)
from common.models.northtext.webhooks import WebhookCreateRequest, Webhook, WebhookDeleteResponse
from common.services.base import BaseService


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

    def api_call(self, method: str, endpoint: str, data: str = None, json: dict = None) -> dict:
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
            raise Exception(r.text)
        return r.json()

    def get_message(self, message_id: int) -> MessageResponse:
        response = self.northtext_client.api_call(
            method='get',
            endpoint=f"/api/v2/message/{message_id}"
        )
        return MessageResponse.model_validate(response)

    def get_messages(
        self,
        limit: int = 100,
        page: int = 0,
        order: str = 'ASC',
        contact_id: int = None
    ) -> MessagesResponse:
        contact_param = f"&Contact={contact_id}" if contact_id else ''
        response = self.api_call('get', f"/api/v2/message?Limit={limit}&Page={page}&Order={order}{contact_param}")
        return MessagesResponse.model_validate(response)

    def send_message(self, message: MessageSendRequest) -> Message:
        response = self.api_call(
            method='post',
            endpoint=f"/api/v2/message",
            json=message.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Message.model_validate(response)

    def send_messages(
        self,
        messages: List[MessageSendRequest]
    ) -> BulkMessagesResponse:
        return self.northtext_client.api_call(
            method='post',
            endpoint='/api/v2/message/bulk',
            json=[m.model_dump(by_alias=True, exclude_unset=True, exclude_none=True) for m in messages]
        )

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

    def create_contact(self, contact: ContactCreateRequest) -> Contact:
        response = self.api_call(
            method='post',
            endpoint=f"/api/v2/contact",
            json=contact.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Contact.model_validate(response)

    def get_contact(self, contact_id: int) -> Contact:
        response = self.api_call(
            method='get',
            endpoint=f"/api/v2/contact/{contact_id}"
        )
        return Contact.model_validate(response)

    def update_contact(self, contact_id: int, contact: Contact) -> Contact:
        response = self.api_call(
            'put',
            f"/api/v2/contact/{contact_id}",
            json=contact.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Contact.model_validate(response)

    def create_webhook(self, webhook: WebhookCreateRequest) -> Webhook:
        response = self.northtext_client.api_call(
            method='post',
            endpoint='/api/v2/webhook',
            json=webhook.model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
        )
        return Webhook.model_validate(response)

    def delete_webhook(self, webhook_id: int) -> WebhookDeleteResponse:
        response = self.northtext_client.api_call(
            method='delete',
            endpoint=f'/api/v2/webhook/{webhook_id}'
        )
        return WebhookDeleteResponse.model_validate(response)
