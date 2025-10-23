from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, Union, Tuple

from firedantic import ModelNotFoundError, configure
from firedantic.common import OrderDirection
from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from hubspot.crm.schemas import ObjectSchema

from common.core.utils import timed_lru_cache
from common.logging.client import Logger
from common.models.firestore.connections import Connection
from common.models.firestore.installations import Installation
from common.models.hubspot.workflow_actions import WorkflowOptionsResponse
from common.models.oauth.tokens import Token
from common.services.base import BaseService
from common.models.monday.monday_integrations import (
    MondayIntegration,
    IntegrationHistory,
)
from google.cloud.firestore_v1.transaction import Transaction


class FirestoreService(BaseService):
    def __init__(
        self,
        firestore_client: firestore.Client,
        logger: Logger | None = None,
    ) -> None:
        self.firestore_client = firestore_client
        configure(self.firestore_client)
        super().__init__(
            log_name="firestore.service",
            logger=logger,
        )

    def get_job(self, monday_integration_id, function_name: str):
        job_doc = self.firestore_client.collection("jobs").document(
            str(monday_integration_id)
        )
        if not job_doc.get().exists:
            new_job = {"completion_time": 0, "function": function_name}
            job_doc.set(document_data=new_job)
        return job_doc.get().to_dict()

    def complete_job(self, monday_integration_id):
        job_doc = self.firestore_client.collection("jobs").document(
            str(monday_integration_id)
        )
        data = job_doc.get().to_dict()
        data["completion_time"] = datetime.now(tz=timezone.utc).timestamp()
        job_doc.set(document_data=data)

    @staticmethod
    def get_connection_by_app_name(installation_id: str, app_name: str) -> Connection:
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one({"app_name": app_name})

    @staticmethod
    def get_active_connection_by_app_name(
        installation_id: str, app_name: str
    ) -> Connection:
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one({"app_name": app_name, "connected": True})

    @staticmethod
    def get_connection_by_app_account_identifier(
        integration_name: str, account_identifier: int | str, app_name: str
    ) -> Connection:
        installation = Installation.find_one(
            {
                "account_identifier": str(account_identifier),
                "integration_name": integration_name,
                "active": True,
            }
        )
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one({"app_name": app_name})

    @staticmethod
    def get_connection_by_app_account_identifier_and_user_id(
        integration_name: str,
        account_identifier: int | str,
        app_name: str,
        user_id: str,
        logger: Logger | None = None,
    ) -> Connection:
        installation = Installation.find_one(
            {
                "account_identifier": str(account_identifier),
                "integration_name": integration_name,
                "active": True,
            }
        )
        if not logger:
            logger = Logger(log_name="firestore.service")
        logger.info(
            f"Installation found for account identifier {account_identifier}: {installation.model_dump_json()}"
        )
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one(
            {"app_name": app_name, "authorized_by_id": user_id}
        )

    @staticmethod
    def get_connection_by_authorized_user(
        installation: Installation,
        app_name: str,
        authorized_by_id: str,
        logger: Logger | None = None,
    ) -> Connection:
        if not logger:
            logger = Logger(log_name="firestore.service")
        logger.info(
            f"Getting connection for account intstallation: {installation.model_dump_json()}"
        )
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one(
            {"app_name": app_name, "authorized_by_id": authorized_by_id}
        )

    @staticmethod
    def get_connection_by_account_identifier(
        installation_id: str, app_name: str, account_identifier: int | str
    ) -> Connection:
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find_one(
            {"app_name": app_name, "account_identifier": account_identifier}
        )

    @staticmethod
    def create_connection(installation_id: str, connection: Connection) -> Connection:
        Connection.__collection__ = f"installations/{installation_id}/connections"
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)
        new_connection = connection_model(**connection.model_dump(exclude_unset=True))
        new_connection.save(exclude_unset=True)
        return new_connection

    @staticmethod
    def get_connection_by_id(installation_id: str, connection_id: str) -> Connection:
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)

        try:
            connection = connection_model.get_by_id(connection_id)
        except ModelNotFoundError:
            connection = connection_model()
        return connection

    @staticmethod
    def get_connections_for_installation(installation_id: str) -> List[Connection]:
        installation = Installation.get_by_id(installation_id)
        connection_model: Type[Connection] = Connection.model_for(installation)
        return connection_model.find()

    @staticmethod
    def get_integration_histories(
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

    def get_app_docs(self):
        return self.firestore_client.collection("apps").list_documents()

    def get_app_doc_field(self, app_name: str, field_name: str) -> Any:
        app_doc = self.firestore_client.collection("apps").document(app_name)

        if not app_doc.get().exists:
            app_doc.set({"created": datetime.now(tz=timezone.utc)})
        doc_data = dict() if not app_doc.get().exists else app_doc.get().to_dict()
        return doc_data.get(field_name)

    def get_account_doc(self, app_name: str, account_id: int | str):
        app_doc = self.firestore_client.collection("apps").document(app_name)
        if not app_doc.get().exists:
            app_doc.set({"created": datetime.now(tz=timezone.utc)})

        account_doc = app_doc.collection("accounts").document(str(account_id))
        if not account_doc.get().exists:
            account_doc.set({"created": datetime.now(tz=timezone.utc)})
        return account_doc

    @timed_lru_cache(seconds=180)
    def get_account_connection(self, app_name: str, account_id: int | str) -> Token:
        connection_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("settings")
            .document("connection")
            .get()
        )
        if not connection_doc.exists:
            raise ConnectionNotFoundException(
                message=f"{app_name} connection for account id {account_id} not found."
            )
        return Token(**connection_doc.to_dict())

    def set_account_connection(self, app_name: str, account_id: int | str, token: dict):
        if "expires_in" in token:
            token["expires_at"] = int(
                (
                    datetime.now(tz=timezone.utc)
                    + timedelta(seconds=token["expires_in"] - 60)
                ).timestamp()
            )
        connection_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("settings")
            .document("connection")
        )
        connection_doc.update(
            token
        ) if connection_doc.get().exists else connection_doc.set(document_data=token)

    def get_object_schema(self, app_name: str, account_id: Any, object_type: str):
        objects_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("settings")
            .document("objects")
        )
        if not objects_doc.get().exists:
            objects_doc.set({"created": datetime.now(tz=timezone.utc)})
        doc = objects_doc.collection(object_type).document("schema")
        object_schema = (
            dict() if not doc.get().exists else ObjectSchema(**doc.get().to_dict())
        )
        return object_schema

    def set_object_schema(
        self,
        app_name: str,
        account_id: str,
        object_type: str,
        object_schema: ObjectSchema,
    ):
        objects_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("settings")
            .document("objects")
        )
        if not objects_doc.get().exists:
            objects_doc.set({"created": datetime.now(tz=timezone.utc)})
        doc = objects_doc.collection(object_type).document("schema")
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        doc.set(document_data=doc_data | object_schema.to_dict())

    def get_app_account_ids(self, app_name: str):
        collection = (
            self.firestore_client.collection("apps")
            .document(document_id=app_name)
            .collection("accounts")
        )

        return [account_doc.id for account_doc in collection.stream()]

    def get_app_account_field(self, app_name: str, account_id: Any, field_name: str):
        doc = self.get_account_doc(app_name=app_name, account_id=str(account_id))
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        return doc_data.get(field_name)

    def set_app_account_field(
        self, app_name: str, account_id: Any, field_name: str, value: Any = None
    ):
        doc = self.get_account_doc(app_name=app_name, account_id=account_id)
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        doc_data[field_name] = value
        return doc.set(document_data=doc_data)

    def get_app_account_usage_doc(
        self, app_name: str, account_id: Any, usage_doc_id: str
    ):
        doc = (
            self.get_account_doc(app_name=app_name, account_id=str(account_id))
            .collection("usage")
            .document(usage_doc_id)
        )
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        return doc_data

    def set_app_account_usage_doc(
        self, app_name: str, account_id: Any, usage_doc_id: str, doc_data: dict
    ):
        doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("usage")
            .document(usage_doc_id)
        )
        return doc.set(document_data=doc_data)

    def record_usage(
        self,
        app_name: str,
        account_id: Any,
        usage_doc_id: str,
        records_processed: int = 0,
    ):
        usage_doc = (
            self.get_account_doc(app_name=app_name, account_id=str(account_id))
            .collection("usage")
            .document(usage_doc_id)
        )
        if not usage_doc.get().exists:
            usage_data = {"quantity": 1, "records_processed": records_processed}
        else:
            usage_data = usage_doc.get().to_dict()
            usage_data["quantity"] += 1
            usage_data["records_processed"] += records_processed
        usage_doc.set(document_data=usage_data)

    def get_object_properties(
        self,
        app_name: str,
        account_id: int | str,
        object_type: str,
        field_type: str = None,
        referenced_object_type: str = None,
    ):
        field_type = field_type if field_type else ""
        referenced_object_type = (
            referenced_object_type if referenced_object_type else ""
        )
        properties_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("object_properties")
            .document(f"{object_type}-{field_type}{referenced_object_type}")
            .get()
        )
        return (
            properties_doc.to_dict()
            if properties_doc.exists
            else WorkflowOptionsResponse(options=[]).model_dump()
        )

    def set_object_properties(
        self,
        app_name: str,
        account_id: int | str,
        object_type: str,
        object_properties: dict,
        field_type: str = "",
        referenced_object_type: str = "",
    ):
        objects_doc = (
            self.get_account_doc(app_name=app_name, account_id=account_id)
            .collection("object_properties")
            .document(f"{object_type}-{field_type}{referenced_object_type}")
        )
        objects_doc.set(document_data=object_properties)

    def delete_account(self, app_name: str, account_id: Any):
        account_doc = self.get_account_doc(app_name=app_name, account_id=account_id)
        self.firestore_client.recursive_delete(reference=account_doc)

    def delete_doc(self, doc_ref: Any):
        self.firestore_client.recursive_delete(reference=doc_ref)

    def read_recursive(
        self,
        source: firestore.CollectionReference,
        target: firestore.CollectionReference,
        batch: firestore.WriteBatch,
    ) -> None:
        batch_nr = 0

        for source_doc_ref in source.stream():
            document_data = source_doc_ref.to_dict()
            target_doc_ref = target.document(source_doc_ref.id)
            if batch_nr == 500:
                print("Committing %s batched operations..." % batch_nr)
                batch.commit()
                batch_nr = 0
            batch.set(
                reference=target_doc_ref,
                document_data=document_data,
                merge=False,
            )
            batch_nr += 1
            for source_coll_ref in source.document(source_doc_ref.id).collections():
                target_coll_ref = target_doc_ref.collection(source_coll_ref.id)
                self.read_recursive(
                    source=source_coll_ref,
                    target=target_coll_ref,
                    batch=batch,
                )

    def copy_collection(
        self,
        source: str,
        target: str,
    ):
        batch = self.firestore_client.batch()
        self.read_recursive(
            source=self.firestore_client.collection(source),
            target=self.firestore_client.collection(target),
            batch=batch,
        )
        batch.commit()

    def object_currently_enrolled(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int,
        callback_id: str,
        expiration_hours: int = 0,
    ):
        enrollment_key = (
            f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        )
        enrollment_doc = self.firestore_client.collection("enrollments").document(
            enrollment_key
        )
        now = datetime.now(tz=timezone.utc)
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        if not doc.exists or doc_obj["expires"] < now:
            enrollment_doc.set(
                {
                    "expires": now + timedelta(hours=expiration_hours),
                    "callback_ids": [callback_id],
                    "completed": False,
                }
            )
            return False
        enrollment_doc.set(
            {
                "expires": doc_obj["expires"],
                "callback_ids": list(set(doc_obj["callback_ids"] + [callback_id])),
                "completed": doc_obj["completed"],
            }
        )

        if not doc_obj["completed"]:
            return True
        return False

    def get_enrollments(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int,
        callback_id: str,
    ):
        enrollment_key = (
            f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        )
        enrollment_doc = self.firestore_client.collection("enrollments").document(
            enrollment_key
        )
        if not enrollment_doc.get().exists:
            return [callback_id]
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        callback_ids = list(set(doc_obj["callback_ids"] + [callback_id]))
        return callback_ids

    def complete_enrollment(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int,
    ):
        enrollment_key = (
            f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        )
        enrollment_doc = self.firestore_client.collection("enrollments").document(
            enrollment_key
        )
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        enrollment_doc.set(
            {
                "expires": enrollment_doc.get().to_dict()["expires"],
                "callback_ids": doc_obj["callback_ids"],
                "completed": True,
            }
        )

    def clear_enrollments(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int,
    ):
        enrollment_key = (
            f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        )
        enrollment_doc = self.firestore_client.collection("enrollments").document(
            enrollment_key
        )
        data = enrollment_doc.get().to_dict()
        data["callback_ids"] = []
        enrollment_doc.set(data)

    def enroll_object_for_bulk_processing(
        self,
        app_name: str,
        function_name: str,
        enrollment_key: str,
        portal_id: Any,
        data: dict,
        callback_id: str = None,
        expiration_hours: int = 0,
    ):
        enrollment_doc = (
            self.get_account_doc(app_name=app_name, account_id=portal_id)
            .collection(f"{function_name}_enrollments")
            .document(enrollment_key)
        )
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        current_callbacks = doc_obj["callback_ids"] if doc.exists else []
        data = {
            "timestamp": datetime.now(tz=timezone.utc),
            "callback_ids": list(set(current_callbacks + [callback_id]))
            if callback_id
            else None,
            "request": data,
            "action_taken": doc_obj["action_taken"] if doc.exists else False,
            "usage_reported": doc_obj["usage_reported"] if doc.exists else False,
            "completed": doc_obj["completed"] if doc.exists else False,
            "expires": doc_obj["expires"]
            if doc.exists
            else datetime.now(tz=timezone.utc) + timedelta(hours=expiration_hours),
            "task_id": "",
            "uuid": "",
        }
        enrollment_doc.set(document_data=data)
        return data

    def update_bulk_enrollments(
        self,
        app_name: str,
        portal_id: Any,
        function_name: str,
        enrollment_ids: List[str],
        merge_data: dict,
    ):
        chunk_size = 500
        enrollments_collection = self.get_account_doc(
            app_name=app_name, account_id=portal_id
        ).collection(f"{function_name}_enrollments")
        while enrollment_ids:
            batch = self.firestore_client.batch()
            chunk, enrollment_ids = (
                enrollment_ids[:chunk_size],
                enrollment_ids[chunk_size:],
            )
            for enrollment_id in chunk:
                enrollment_doc = enrollments_collection.document(enrollment_id)
                if enrollment_doc.get().exists:
                    batch.update(enrollment_doc, merge_data)
                else:
                    batch.set(enrollment_doc, merge_data)
            batch.commit()

    def get_bulk_enrollments(self, app_name: str, portal_id: Any, function_name: str):
        return (
            self.get_account_doc(app_name=app_name, account_id=portal_id)
            .collection(f"{function_name}_enrollments")
            .where(
                filter=FieldFilter(field_path="completed", op_string="==", value=False)
            )
        )

    def get_bulk_enrollments_by_field(
        self,
        app_name: str,
        portal_id: Any,
        function_name: str,
        field_name: str,
        field_value: Any,
    ):
        return (
            self.get_account_doc(app_name=app_name, account_id=portal_id)
            .collection(f"{function_name}_enrollments")
            .where(
                filter=FieldFilter(
                    field_path=field_name, op_string="==", value=field_value
                )
            )
        )


class ConnectionNotFoundException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
