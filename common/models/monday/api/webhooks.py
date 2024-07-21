from typing import Optional

from pydantic import BaseModel


class WebhookResponse(BaseModel):
    id: Optional[int] = None
    board_id: Optional[int] = None
