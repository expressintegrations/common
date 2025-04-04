import os
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from common.services.base import BaseService


class AsyncFirestoreService(BaseService):
    def __init__(self, firestore_client: firestore.AsyncClient = None) -> None:
        if firestore_client is None:
            self.firestore_client = firestore.AsyncClient()
        else:
            self.firestore_client = firestore_client
        super().__init__(
            log_name="firestore.service",
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
