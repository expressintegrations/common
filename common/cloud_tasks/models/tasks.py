from pydantic import BaseModel


class OidcTokenConfig(BaseModel):
    """OIDC token configuration for a task."""

    service_account_email: str
    audience: str
