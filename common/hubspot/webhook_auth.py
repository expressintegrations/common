from dataclasses import dataclass
import base64
import hashlib
import hmac


@dataclass
class ValidationError:
    message: str
    error_type: str


class HubSpotWebhookValidator:
    webhook_secret: str

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret

    def verify_signature(
        self,
        x_hubspot_signature_v3: str,
        x_hubspot_request_timestamp: str,
        request_method: str,
        request_url: str,
        payload: bytes,
    ) -> tuple[bool, ValidationError | None]:
        if not x_hubspot_signature_v3:
            return False, ValidationError(
                "Missing x-hubspot-signature-v3 header", "missing_signature"
            )

        if not x_hubspot_request_timestamp:
            return False, ValidationError(
                "Missing x-hubspot-request-timestamp header", "missing_timestamp"
            )
        message = (
            f"{request_method}{request_url.replace('http://', 'https://')}{payload.decode()}"
            f"{x_hubspot_request_timestamp}"
        )
        computed_sha = hmac.new(
            key=self.webhook_secret.encode(),
            msg=message.encode(),
            digestmod=hashlib.sha256,
        )
        my_sig = base64.b64encode(computed_sha.digest()).decode()
        if my_sig != x_hubspot_signature_v3:
            return False, ValidationError(
                "Signature mismatch: {my_sig} != {x_hubspot_signature_v3}",
                "signature_mismatch",
            )

        return True, None
