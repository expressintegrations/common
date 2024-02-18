from enum import Enum
from typing import List

from pydantic import BaseModel


class SyncDirection(str, Enum):
    INCOMING = '⟶'
    OUTGOING = '⟵'
    BI_DIRECTIONAL = '⟷'


class ContactSyncMapping(BaseModel):
    northtext: str
    hubspot: str


class ContactSyncRequest(BaseModel):
    portal_id: int
    sync_direction: SyncDirection
    sync_last_checked: int
    mappings: List[ContactSyncMapping]
