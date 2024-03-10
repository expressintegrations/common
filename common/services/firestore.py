from datetime import datetime, timedelta, timezone
from typing import Any, List

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from hubspot.crm.schemas import ObjectSchema

from common.core.utils import timed_lru_cache
from common.models.hubspot.workflow_actions import WorkflowOptionsResponse
from common.models.oauth.tokens import Token
from common.services.base import BaseService


class FirestoreService(BaseService):
    def __init__(
        self,
        firestore_client: firestore.Client
    ) -> None:
        self.firestore_client = firestore_client
        super().__init__(
            log_name='firestore.service',
            exclude_inputs=[
                'set_account_connection'
            ],
            exclude_outputs=[
                'get_account_connection'
            ]
        )

    def get_app_docs(self):
        return self.firestore_client.collection('apps').list_documents()

    def get_app_doc_field(self, app_name: str, field_name: str) -> Any:
        app_doc = self.firestore_client.collection('apps').document(
            app_name
        )

        if not app_doc.get().exists:
            app_doc.set(
                {'created': datetime.now()}
            )
        doc_data = dict() if not app_doc.get().exists else app_doc.get().to_dict()
        return doc_data.get(field_name)

    def get_account_doc(self, app_name: str, account_id: [int | str]):
        app_doc = self.firestore_client.collection(
            'apps'
        ).document(
            app_name
        )
        if not app_doc.get().exists:
            app_doc.set(
                {'created': datetime.now()}
            )

        account_doc = app_doc.collection(
            'accounts'
        ).document(
            str(account_id)
        )
        if not account_doc.get().exists:
            account_doc.set(
                {'created': datetime.now()}
            )
        return account_doc

    @timed_lru_cache(seconds=180)
    def get_account_connection(self, app_name: str, account_id: [int | str]) -> Token:
        connection_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'settings'
        ).document(
            'connection'
        ).get()
        if not connection_doc.exists:
            raise ConnectionNotFoundException(message=f"{app_name} connection for account id {account_id} not found.")
        return Token(**connection_doc.to_dict())

    def set_account_connection(self, app_name: str, account_id: [int | str], token: dict):
        if 'expires_in' in token:
            token['expires_at'] = int((datetime.now() + timedelta(seconds=token['expires_in'] - 60)).timestamp())
        connection_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'settings'
        ).document(
            'connection'
        )
        connection_doc.update(token) if connection_doc.get().exists else connection_doc.set(document_data=token)

    def get_object_schema(self, app_name: str, account_id: Any, object_type: str):
        objects_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'settings'
        ).document(
            'objects'
        )
        if not objects_doc.get().exists:
            objects_doc.set(
                {'created': datetime.now()}
            )
        doc = objects_doc.collection(
            object_type
        ).document('schema')
        object_schema = dict() if not doc.get().exists else ObjectSchema(**doc.get().to_dict())
        return object_schema

    def set_object_schema(self, app_name: str, account_id: str, object_type: str, object_schema: ObjectSchema):
        objects_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'settings'
        ).document(
            'objects'
        )
        if not objects_doc.get().exists:
            objects_doc.set(
                {'created': datetime.now()}
            )
        doc = objects_doc.collection(
            object_type
        ).document('schema')
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        doc.set(document_data=doc_data | object_schema.to_dict())

    def get_app_account_ids(self, app_name: str):
        collection = self.firestore_client.collection('apps').document(
            document_id=app_name
        ).collection('accounts')

        return [account_doc.id for account_doc in collection.stream()]

    def get_app_account_field(self, app_name: str, account_id: Any, field_name: str):
        doc = self.get_account_doc(
            app_name=app_name,
            account_id=str(account_id)
        )
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        return doc_data.get(field_name)

    def set_app_account_field(self, app_name: str, account_id: Any, field_name: str, value: Any = None):
        doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        )
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        doc_data[field_name] = value
        return doc.set(document_data=doc_data)

    def get_app_account_usage_doc(self, app_name: str, account_id: Any, usage_doc_id: str):
        doc = self.get_account_doc(
            app_name=app_name,
            account_id=str(account_id)
        ).collection(
            'usage'
        ).document(
            usage_doc_id
        )
        doc_data = dict() if not doc.get().exists else doc.get().to_dict()
        return doc_data

    def set_app_account_usage_doc(self, app_name: str, account_id: Any, usage_doc_id: str, doc_data: dict):
        doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'usage'
        ).document(
            usage_doc_id
        )
        return doc.set(document_data=doc_data)

    def record_usage(
        self,
        app_name: str,
        account_id: Any,
        usage_doc_id: str,
        records_processed: int = 0
    ):
        usage_doc = self.get_account_doc(
            app_name=app_name,
            account_id=str(account_id)
        ).collection(
            'usage'
        ).document(
            usage_doc_id
        )
        if not usage_doc.get().exists:
            usage_data = {
                'quantity': 1,
                'records_processed': records_processed
            }
        else:
            usage_data = usage_doc.get().to_dict()
            usage_data['quantity'] += 1
            usage_data['records_processed'] += records_processed
        usage_doc.set(document_data=usage_data)

    def get_object_properties(
        self,
        app_name: str,
        account_id: [int | str],
        object_type: str,
        field_type: str = None,
        referenced_object_type: str = None
    ):
        field_type = field_type if field_type else ''
        referenced_object_type = referenced_object_type if referenced_object_type else ''
        properties_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'object_properties'
        ).document(
            f"{object_type}-{field_type}{referenced_object_type}"
        ).get()
        return properties_doc.to_dict() if properties_doc.exists else WorkflowOptionsResponse(options=[]).model_dump()

    def set_object_properties(
        self,
        app_name: str,
        account_id: [int | str],
        object_type: str,
        object_properties: dict,
        field_type: str = '',
        referenced_object_type: str = ''
    ):
        objects_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        ).collection(
            'object_properties'
        ).document(
            f"{object_type}-{field_type}{referenced_object_type}"
        )
        objects_doc.set(document_data=object_properties)

    def delete_account(self, app_name: str, account_id: Any):
        account_doc = self.get_account_doc(
            app_name=app_name,
            account_id=account_id
        )
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
        expiration_hours: int = 0
    ):
        enrollment_key = f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        enrollment_doc = self.firestore_client.collection(
            'enrollments'
        ).document(
            enrollment_key
        )
        now = datetime.now(tz=timezone.utc)
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        if not doc.exists or doc_obj['expires'] < now:
            enrollment_doc.set(
                {
                    'expires': now + timedelta(hours=expiration_hours),
                    'callback_ids': [callback_id],
                    'completed': False
                }
            )
            return False
        enrollment_doc.set(
            {
                'expires': doc_obj['expires'],
                'callback_ids': list(set(doc_obj['callback_ids'] + [callback_id])),
                'completed': doc_obj['completed']
            }
        )

        if not doc_obj['completed']:
            return True
        return False

    def get_enrollments(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int,
        callback_id: str
    ):
        enrollment_key = f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        enrollment_doc = self.firestore_client.collection(
            'enrollments'
        ).document(
            enrollment_key
        )
        if not enrollment_doc.get().exists:
            return [callback_id]
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        callback_ids = list(set(doc_obj['callback_ids'] + [callback_id]))
        return callback_ids

    def complete_enrollment(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int
    ):
        enrollment_key = f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        enrollment_doc = self.firestore_client.collection(
            'enrollments'
        ).document(
            enrollment_key
        )
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        enrollment_doc.set(
            {
                'expires': enrollment_doc.get().to_dict()['expires'],
                'callback_ids': doc_obj['callback_ids'],
                'completed': True
            }
        )

    def clear_enrollments(
        self,
        portal_id: int,
        workflow_id: int,
        action_id: int,
        object_type: str,
        object_id: int
    ):
        enrollment_key = f"{portal_id}-{workflow_id}-{action_id}-{object_type}-{object_id}"
        enrollment_doc = self.firestore_client.collection(
            'enrollments'
        ).document(
            enrollment_key
        )
        data = enrollment_doc.get().to_dict()
        data['callback_ids'] = []
        enrollment_doc.set(data)

    def enroll_object_for_bulk_processing(
        self,
        app_name: str,
        function_name: str,
        enrollment_key: str,
        portal_id: Any,
        data: dict,
        callback_id: str = None,
        expiration_hours: int = 0
    ):
        enrollment_doc = self.get_account_doc(
            app_name=app_name,
            account_id=portal_id
        ).collection(
            f'{function_name}_enrollments'
        ).document(
            enrollment_key
        )
        doc = enrollment_doc.get()
        doc_obj = doc.to_dict()
        current_callbacks = doc_obj['callback_ids'] if doc.exists else []
        data = {
            'timestamp': datetime.now(),
            'callback_ids': list(set(current_callbacks + [callback_id])) if callback_id else None,
            'request': data,
            'action_taken': doc_obj['action_taken'] if doc.exists else False,
            'usage_reported': doc_obj['usage_reported'] if doc.exists else False,
            'completed': doc_obj['completed'] if doc.exists else False,
            'expires': doc_obj['expires'] if doc.exists else datetime.now() + timedelta(hours=expiration_hours)
        }
        enrollment_doc.set(document_data=data)
        return data

    def update_bulk_enrollments(
        self,
        app_name: str,
        portal_id: Any,
        function_name: str,
        enrollment_ids: List[str],
        merge_data: dict
    ):
        chunk_size = 500
        enrollments_collection = self.get_account_doc(
            app_name=app_name,
            account_id=portal_id
        ).collection(
            f'{function_name}_enrollments'
        )
        while enrollment_ids:
            batch = self.firestore_client.batch()
            chunk, enrollment_ids = enrollment_ids[:chunk_size], enrollment_ids[chunk_size:]
            for enrollment_id in chunk:
                enrollment_doc = enrollments_collection.document(
                    enrollment_id
                )
                batch.update(enrollment_doc, merge_data)
            batch.commit()

    def get_bulk_enrollments(
        self,
        app_name: str,
        portal_id: Any,
        function_name: str
    ):
        return self.get_account_doc(
            app_name=app_name,
            account_id=portal_id
        ).collection(
            f'{function_name}_enrollments'
        ).where(
            filter=FieldFilter(
                field_path="completed",
                op_string="==",
                value=False
            )
        ).limit(1000)


class ConnectionNotFoundException(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self):
        return self.message
