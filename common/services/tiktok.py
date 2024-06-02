import time
import hashlib
import hmac
from datetime import datetime

import requests

from common.models.tiktok.auth import Authorization
from common.services.base import BaseService


class TikTokService(BaseService):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    base_url = 'https://open-api.tiktokglobalshop.com/api/'

    def __init__(
        self,
        access_token: str,
        app_key: str,
        app_secret: str
    ) -> None:
        self.access_token = access_token
        self.app_key = app_key
        self.app_secret = app_secret
        super().__init__(log_name='tiktok.service')

    @staticmethod
    def authorize_token(app_key: str, app_secret: str, auth_code: str) -> Authorization:
        response = requests.get(
            url='https://auth.tiktok-shops.com/api/v2/token/get',
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            params={
                "app_key": app_key,
                "auth_code": auth_code,
                "app_secret": app_secret,
                "grant_type": "authorized_code"
            }
        )
        return Authorization.model_validate(response.json())

    @staticmethod
    def refresh_token(refresh_token: str, app_key: str, app_secret: str) -> Authorization:
        response = requests.get(
            url='https://auth.tiktok-shops.com/api/v2/token/refresh',
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            params={
                "app_key": app_key,
                "app_secret": app_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
        return Authorization.model_validate(response.json())

    def api_call(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        data: str = None,
        json: [dict | list] = None
    ) -> dict:
        auth_params = {
            "app_key": self.app_key,
            "timestamp": datetime.now().timestamp()
        }
        params |= auth_params
        base_string = f"/api/{endpoint}"
        for k, v in params.items():
            if k not in ['sign', 'access_token']:
                base_string += f"{k}{v}"
        auth_string = f"{self.app_key}{base_string}{self.app_key}"
        computed_sha = hmac.new(
            key=self.app_secret.encode(),
            msg=auth_string.encode(),
            digestmod=hashlib.sha256
        )
        signature = computed_sha.hexdigest()
        params['sign'] = signature
        params['access_token'] = self.access_token
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
