import os
from datetime import datetime, timedelta, timezone

from google.cloud import firestore
from typing import Dict, List, Optional, Type, Union, Tuple
from firedantic.common import OrderDirection

from common.services.base import BaseService
from common.models.monday.monday_integrations import (
    MondayIntegration,
    IntegrationHistory,
)
from google.cloud.firestore_v1.transaction import Transaction


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
