from pydantic import BaseModel


class SimpleBoard(BaseModel):
    id: str
    name: str
