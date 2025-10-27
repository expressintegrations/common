import os
from datetime import datetime, timedelta, timezone, UTC

from google.cloud import firestore
from typing import Dict, List, Optional, Type, Union, Tuple
from firedantic.common import OrderDirection
from firedantic import ModelNotFoundError

from common.services.base import BaseService
from common.models.monday.monday_integrations import (
    MondayIntegration,
    IntegrationHistory,
)
from google.cloud.firestore_v1.transaction import Transaction
from pydantic import BaseModel


class Lock(BaseModel):
    expires_at: datetime
    expiration_seconds: int
    locked: bool
    owner: str


class AsyncFirestoreService(BaseService):
    def __init__(self, firestore_client: firestore.AsyncClient | None = None) -> None:
        if firestore_client is None:
            self.firestore_client = firestore.AsyncClient()
        else:
            self.firestore_client = firestore_client
        super().__init__(
            log_name="firestore.service",
        )

    async def acquire_lock_for_owner(
        self, lock_id: str, owner: str, expiration_seconds: int = 60
    ) -> tuple[bool, Lock]:
        transaction = self.firestore_client.transaction()

        lock_ref = self.firestore_client.collection("locks").document(lock_id)
        lock_data = {
            "expires_at": firestore.SERVER_TIMESTAMP,
            "expiration_seconds": expiration_seconds,
            "locked": True,
            "owner": owner,
        }

        @firestore.async_transactional
        async def update_in_transaction(transaction: Transaction) -> bool:
            snapshot = await lock_ref.get(transaction=transaction)
            if not snapshot.exists:
                transaction.set(lock_ref, lock_data)
                return True
            existing_lock = snapshot.to_dict()
            if existing_lock is None:
                transaction.set(lock_ref, lock_data)
                return True
            expires_at = existing_lock.get("expires_at")
            expiration_seconds = existing_lock.get("expiration_seconds")

            # If the lock exists and hasn't expired, check if it's owned by the same owner
            if (
                expires_at is not None
                and expiration_seconds is not None
                and expires_at + timedelta(seconds=expiration_seconds)
                > datetime.now(UTC)
            ):
                # If same owner, allow re-acquisition
                if existing_lock.get("owner") == owner:
                    return True
                # If different owner, deny acquisition
                return False
            # If the lock exists and has expired, allow acquisition
            transaction.set(lock_ref, lock_data)
            return True

        lock_acquired = await update_in_transaction(transaction)

        if not lock_acquired:
            # Get the existing lock
            snapshot = await lock_ref.get()
            if not snapshot.exists or snapshot.to_dict() is None:
                # Lock was deleted between transaction and retrieval
                # Return a placeholder lock indicating it's held by unknown owner
                return False, Lock(
                    expires_at=datetime.now(UTC) + timedelta(seconds=expiration_seconds),
                    expiration_seconds=expiration_seconds,
                    locked=True,
                    owner="unknown",
                )
            return False, Lock.model_validate(snapshot.to_dict())

        # Get the actual lock data from Firestore to get the real expiration
        snapshot = await lock_ref.get()
        if snapshot.exists:
            return True, Lock.model_validate(snapshot.to_dict())

        # Fallback to estimated time if lock doesn't exist (shouldn't happen)
        estimated_expires_at = datetime.now(UTC) + timedelta(seconds=expiration_seconds)
        return True, Lock(
            expires_at=estimated_expires_at,
            expiration_seconds=expiration_seconds,
            locked=True,
            owner=owner,
        )

    async def acquire_lock(self, lock_id: str, expiration_seconds: int = 60) -> bool:
        transaction = self.firestore_client.transaction()

        lock_ref = self.firestore_client.collection("locks").document(lock_id)

        @firestore.async_transactional
        async def update_in_transaction(transaction, lock_ref):
            snapshot = await lock_ref.get(transaction=transaction)
            if snapshot.exists and snapshot.get("expires_at") + timedelta(
                seconds=snapshot.get("expiration_seconds")
            ) > datetime.now(timezone.utc):
                return False
            transaction.set(
                lock_ref,
                {
                    "expires_at": firestore.SERVER_TIMESTAMP,
                    "expiration_seconds": expiration_seconds,
                    "locked": True,
                    "owner": os.environ.get("K_REVISION", "unknown"),
                },
            )

        await update_in_transaction(transaction, lock_ref)
        return True

    async def release_lock(self, lock_id: str) -> None:
        transaction = self.firestore_client.transaction()

        lock_ref = self.firestore_client.collection("locks").document(lock_id)

        @firestore.async_transactional
        async def delete_in_transaction(transaction, lock_ref):
            transaction.delete(
                lock_ref,
            )

        await delete_in_transaction(transaction, lock_ref)

    @staticmethod
    async def get_integration_histories(
        integration_id: str,
        filter_: Optional[Dict[str, Union[str, dict]]] = None,
        order_by: Optional[List[Tuple[str, OrderDirection]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        transaction: Optional[Transaction] = None,
    ) -> List[IntegrationHistory]:
        integration = MondayIntegration.get_by_id(integration_id)
        history_model: Type[IntegrationHistory] = IntegrationHistory.model_for(
            integration
        )
        return history_model.find(
            filter_=filter_,
            order_by=order_by,
            limit=limit,
            offset=offset,
            transaction=transaction,
        )

    @staticmethod
    async def create_integration_history(
        integration_id: str, integration: IntegrationHistory
    ) -> IntegrationHistory:
        IntegrationHistory.__collection__ = (
            f"monday_integrations/{integration_id}/history"
        )
        integration_model: Type[IntegrationHistory] = IntegrationHistory.model_for(
            integration
        )
        new_integration = integration_model(
            **integration.model_dump(exclude_unset=True)
        )
        new_integration.save(exclude_unset=True)
        return new_integration

    @staticmethod
    async def get_integration_history_by_id(
        integration_id: str, history_id: str
    ) -> IntegrationHistory:
        integration = MondayIntegration.get_by_id(integration_id)
        history_model: Type[IntegrationHistory] = IntegrationHistory.model_for(
            integration
        )

        try:
            history = history_model.get_by_id(history_id)
        except ModelNotFoundError:
            history = history_model.model_construct()
            history.id = history_id
        return history
