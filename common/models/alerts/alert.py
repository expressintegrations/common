from typing import Any

from pydantic import BaseModel


class FormsApiError(BaseModel):
    error_message: str
    form_submission: Any
    page_url: str
