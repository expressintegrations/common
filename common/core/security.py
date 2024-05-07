from typing import Union

import jwt
import jwt.algorithms
import requests
from dependency_injector.wiring import inject
from fastapi import HTTPException, status, Header
from jwt import ExpiredSignatureError, InvalidSignatureError, InvalidAudienceError

from common.core.utils import timed_lru_cache
from common.services.metadata import MetadataService

OIDC_ENDPOINT = 'https://accounts.google.com/.well-known/openid-configuration'
CERTS = None


@timed_lru_cache(seconds=30)
def get_google_certs():
    config = requests.get(OIDC_ENDPOINT).json()
    return requests.get(config['jwks_uri']).json()


@inject
def verify_google(
    authorization: Union[str, None] = Header(default=None),
):
    metadata_service = MetadataService()
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Please use a valid token from google.com"
        )

    token = authorization.replace('Bearer ', '')

    global CERTS
    if CERTS is None:
        CERTS = get_google_certs()
    public_keys = {}
    for jwk in CERTS['keys']:
        kid = jwk.get('kid')
        if not kid:
            return
        public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    kid = jwt.get_unverified_header(token)['kid']
    key = public_keys.get(kid)
    if not key:
        return

    try:
        payload = jwt.decode(token, key=key, algorithms=['RS256'], audience=metadata_service.public_url)
        if payload['iss'] != 'https://accounts.google.com':
            print(f"Issuer is invalid: {payload['iss']} != https://accounts.google.com")
            print(f"Failed to validate JWT: {token}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized. Please use a valid token from google"
            )
    except ExpiredSignatureError:
        print(f"Signature has expired for ({token})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature has expired. Please use a valid token from google"
        )
    except InvalidSignatureError:
        print(f"Invalid JWT for ({token})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to validate token. Please use a valid token from google"
        )
    except InvalidAudienceError:
        print(f"Invalid audience for ({token})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to validate token. Please use a valid token from google"
        )
