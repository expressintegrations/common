from pydantic import BaseModel


class ReplicationSummary(BaseModel):
    columns_added: int | None = None
    columns_dropped: int | None = None
    columns_retyped: int | None = None
