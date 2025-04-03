from dataclasses import dataclass
from functools import cached_property

import jwt
import jwt.algorithms
import requests


@dataclass
class ValidationError:
    message: str
    error_type: str


class GoogleTokenValidator:
    OIDC_ENDPOINT = "https://accounts.google.com/.well-known/openid-configuration"

    @cached_property
    def certs(self) -> dict:
        config = requests.get(GoogleTokenValidator.OIDC_ENDPOINT, timeout=10).json()
        return dict(requests.get(config["jwks_uri"], timeout=10).json())

    def _get_public_keys(self) -> dict:
        public_keys = {}
        for jwk in self.certs["keys"]:
            kid = jwk.get("kid")
            if kid:
                public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        return public_keys

    def verify_token(self, token: str, audience: str) -> tuple[bool, ValidationError | None]:
        public_keys = self._get_public_keys()

        try:
            kid = jwt.get_unverified_header(token)["kid"]
        except jwt.InvalidTokenError:
            return False, ValidationError("Invalid token format", "invalid_token")

        key = public_keys.get(kid)
        if not key:
            return False, ValidationError("Unable to verify token signature", "invalid_key")

        try:
            payload = jwt.decode(token, key=key, algorithms=["RS256"], audience=audience)

            if payload["iss"] != "https://accounts.google.com":
                return False, ValidationError(
                    f"Invalid token issuer: {payload['iss']} != https://accounts.google.com", "invalid_issuer"
                )

            return True, None

        except jwt.ExpiredSignatureError:
            return False, ValidationError("Token has expired", "expired_token")
        except jwt.InvalidSignatureError:
            return False, ValidationError("Invalid token signature", "invalid_signature")
        except jwt.InvalidAudienceError:
            unverified_audience = jwt.decode(token, options={"verify_signature": False}).get("aud")
            return False, ValidationError(
                f"Invalid token audience: {audience} != {unverified_audience}", "invalid_audience"
            )
