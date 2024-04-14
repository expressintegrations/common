from pydantic import BaseModel


class CreateRecordResponse(BaseModel):
    id: str
