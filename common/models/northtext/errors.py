from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status: int
    description: str
