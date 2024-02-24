import json
import os
import re
from datetime import datetime
from functools import cached_property
from typing import Any, List, Union

import hubspot.marketing.events.exceptions
import requests
from hubspot import HubSpot
from hubspot.crm.associations import BatchInputPublicObjectId, BatchInputPublicAssociation
from hubspot.crm.associations.v4 import PublicAssociationDefinitionCreateRequest
from hubspot.crm.objects import (
    SimplePublicObjectInput,
    PublicObjectSearchRequest
)
from hubspot.crm.properties import PropertyGroupCreate, BatchInputPropertyCreate
from hubspot.files.files.exceptions import NotFoundException as HubSpotFileNotFoundException
from hubspot.marketing.events import BatchInputMarketingEventSubscriber
from requests.exceptions import InvalidSchema
from urllib3.util.retry import Retry

from common.core.utils import timed_lru_cache
from common.models.hubspot.marketing_events import MarketingEvent
from common.models.hubspot.settings import HubSpotAccountDetails
from common.models.hubspot.timeline_events import TimelineEvent
from common.models.hubspot.workflow_actions import (
    WorkflowFieldOption, WorkflowOptionsResponse, HubSpotWorkflowException, ErrorCode, HubSpotExecutionState,
    HubSpotWorkflowActionOutputFieldsModel, HubSpotWorkflowActionCallbackBatchModel,
    HubSpotWorkflowActionCallbackModel
)
from common.services import constants
from common.services.base import BaseService

MULTI_URL_REGEX = r'((https?):((//)|(\\\\))+([\w\d:#@%/;$~_?\+-=\\\.&](#!)?)*)'


class HubSpotService(BaseService):
    base_url = "https://api.hubapi.com"

    def __init__(
        self,
        access_token: str
    ) -> None:
        self.access_token = access_token
        retry = Retry(
            total=60,
            backoff_factor=4,
            status_forcelist=(429, 502, 504),
        )
        self.hubspot_client = HubSpot(access_token=access_token, retry=retry)
        super().__init__(
            log_name='hubspot.service',
            exclude_inputs=[
                'create_objects_batch',
                'update_objects_batch',
                'get_objects_batch',
                'create_associations_v4_batch'
            ],
            exclude_outputs=[
                'create_objects_batch',
                'update_objects_batch',
                'get_objects_batch',
                'create_associations_v4_batch',
                'get_all_properties',
                'get_properties_as_workflow_options'
            ]
        )

    def get_account_details(self) -> HubSpotAccountDetails:
        resp = self.hubspot_client.auth.oauth.access_tokens_api.api_client.request(
            method="GET",
            url="https://api.hubapi.com/account-info/v3/details",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
        return HubSpotAccountDetails.model_validate(json.loads(resp.data))

    def get_token_details(self):
        return self.hubspot_client.auth.oauth.access_tokens_api.get(self.access_token)

    def get_authed_user(self):
        return self.get_user(user_id=self.get_token_details().user_id)

    def get_user(self, user_id):
        return self.get_owner_by_id(owner_id=user_id, id_property='userId')

    def get_users(self):
        users_response = self.hubspot_client.settings.users.users_api.get_page()
        users = users_response.results
        while users_response.paging and users_response.paging.next and users_response.paging.next.after:
            users_response = self.hubspot_client.settings.users.users_api.get_page(
                after=users_response.paging.next.after
            )
            users.append(users_response.results)
        return users

    def get_owner_by_id(self, owner_id, id_property: str = 'id'):
        return self.hubspot_client.crm.owners.owners_api.get_by_id(owner_id, id_property=id_property)

    def get_owners(self, archived: bool = False):
        owners_response = self.hubspot_client.crm.owners.owners_api.get_page(archived=archived)
        owners = owners_response.results
        while owners_response.paging and owners_response.paging.next and owners_response.paging.next.after:
            owners_response = self.hubspot_client.crm.owners.owners_api.get_page(
                after=owners_response.paging.next.after,
                archived=archived
            )
            owners.append(owners_response.results)
        if archived:
            users_by_email = {user.email: user for user in self.get_users()}
            for owner in owners:
                user = users_by_email.get(owner.email)
                if not user:
                    owner.teams = []
                    continue
                teams = []
                if user.primary_team_id:
                    teams.append(
                        {
                            'id': user.primary_team_id,
                            'primary': True
                        }
                    )
                if user.secondary_team_ids:
                    teams += [
                        {
                            'id': team_id,
                            'primary': False
                        } for team_id in user.secondary_team_ids
                    ]
                owner.teams = teams
                owner.user_id = user.id
        return owners

    def get_owners_as_workflow_options(self, include_deactivated: bool = False):
        owners = self.get_owners()
        if include_deactivated:
            owners += self.get_owners(archived=True)
        options = [
            WorkflowFieldOption(
                label=(
                    f"{owner.first_name} {owner.last_name}"
                    f"{' - Deactivated' if owner.archived else ''}\n({owner.email})"
                ),
                description=f"{owner.email}",
                value=owner.id
            ) for owner in sorted(owners, key=lambda o: o.email)
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def revoke(self):
        token_details = self.get_token_details()
        application_name = {v['app_id']: k for k, v in self.config['apps'].items()}[token_details.app_id]
        token = self.firestore_service.get_account_connection(
            app_name=application_name,
            account_id=token_details.hub_id
        )
        self.hubspot_client.auth.oauth.refresh_tokens_api.archive_refresh_token(token.refresh_token)

    @timed_lru_cache(seconds=3600)
    def get_team(self, team_id: str):
        for team in self.get_teams:
            if team.id == team_id:
                return team

    @cached_property
    def get_teams(self):
        return self.hubspot_client.settings.users.teams_api.get_all().results

    @cached_property
    def get_teams_as_workflow_options(self):
        teams = self.get_teams
        options = [
            WorkflowFieldOption(
                label=team.name,
                description=team.name,
                value=team.id
            ) for team in sorted(teams, key=lambda t: t.name)
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def create_custom_object(self, object_schema: dict):
        return self.hubspot_client.crm.schemas.core_api.create(
            object_schema_egg=object_schema
        )

    def create_pipeline(self, object_type: str, pipeline: dict):
        return self.hubspot_client.crm.pipelines.pipelines_api.create(
            object_type=object_type,
            pipeline_input=pipeline
        )

    def get_pipeline_stages(self, object_type: str, pipeline_id: str):
        return self.hubspot_client.crm.pipelines.pipeline_stages_api.get_all(
            object_type=object_type,
            pipeline_id=pipeline_id
        )

    @cached_property
    def get_objects_as_workflow_options(self):
        objects = constants.BASE_WORKFLOW_ACTION_OBJECTS
        if 'crm.schemas.custom.read' in self.get_token_details().scopes:
            for custom_object in self.hubspot_client.crm.schemas.core_api.get_all().results:
                objects.append(
                    {
                        "label": custom_object.labels.singular,
                        "value": custom_object.object_type_id
                    }
                )
        unique_objects = list({v['value']: v for v in objects}.values())
        options = [
            WorkflowFieldOption(
                label=obj["label"],
                description=obj["label"],
                value=obj["value"]
            ) for obj in unique_objects
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def get_properties_as_workflow_options(
        self,
        object_type: str,
        field_type: str = None,
        referenced_object_type: str = None
    ):
        properties = self.get_all_properties(object_type=object_type)
        if field_type:
            options = [
                WorkflowFieldOption(
                    label=prop.label,
                    description=prop.label,
                    value=prop.name
                ) for prop in properties.results if prop.field_type == field_type
            ]
        elif referenced_object_type:
            options = [
                WorkflowFieldOption(
                    label=prop.label,
                    description=prop.label,
                    value=prop.name
                ) for prop in properties.results if prop.referenced_object_type == referenced_object_type
            ]
        else:
            options = [
                WorkflowFieldOption(
                    label=prop.label,
                    description=prop.label,
                    value=prop.name
                ) for prop in properties.results
            ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def get_properties_by_field_types(self, object_type: str, field_types: List[str] = None):
        properties = self.get_all_properties(object_type=object_type).to_dict()
        options = [
            prop for prop in properties['results'] if prop['field_type'] in field_types
        ] if field_types else properties['results']
        return options

    def get_pipeline_stages_as_workflow_options(self, object_type: str, pipeline_id: str):
        stages = self.get_pipeline_stages(object_type=object_type, pipeline_id=pipeline_id)
        options = [
            WorkflowFieldOption(
                label=stage.label,
                description=stage.label,
                value=stage.id
            ) for stage in stages.results
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def get_pipelines(self, object_type: str):
        return self.hubspot_client.crm.pipelines.pipelines_api.get_all(object_type=object_type)

    def get_pipelines_as_workflow_options(self, object_type: str):
        pipelines = self.get_pipelines(object_type=object_type)
        options = [
            WorkflowFieldOption(
                label=pipeline.label,
                description=pipeline.label,
                value=pipeline.id
            ) for pipeline in pipelines.results
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def create_property(self, object_type: str, property_dict: dict):
        return self.hubspot_client.crm.properties.core_api.create(
            object_type=object_type,
            property_create=property_dict
        )

    def get_property(self, object_type: str, property_name: str):
        return self.hubspot_client.crm.properties.core_api.get_by_name(
            object_type=object_type,
            property_name=property_name
        )

    def get_all_properties(self, object_type: str):
        return self.hubspot_client.crm.properties.core_api.get_all(
            object_type=object_type
        )

    def update_property(self, object_type: str, property_name: str, property_dict: dict):
        return self.hubspot_client.crm.properties.core_api.update(
            object_type=object_type,
            property_name=property_name,
            property_update=property_dict
        )

    def merge_property_options(
        self,
        object_type: str,
        property_name: str,
        new_options: List[dict],
        option_value_key: str = 'value',
        option_label_key: str = 'label'
    ):
        def parse_option(index, option):
            return {
                'display_order': index + 1,
                'hidden': False,
                'label': str(option[option_label_key]),
                'value': str(option[option_value_key])
            }
        prop = self.get_property(object_type=object_type, property_name=property_name).to_dict()
        new_option_map = {o[option_value_key]: parse_option(i, o) for i, o in enumerate(new_options)}
        for o in prop['options']:
            if o['value'] and len(o['value']) > 0 and o['value'] not in new_option_map:
                new_option_map[o['value']] = o
        if not new_option_map:
            print(f"Unable to update property {object_type}.{property_name}. At least one option is required.")
            return
        prop['options'] = list(new_option_map.values())
        return self.update_property(object_type=object_type, property_name=property_name, property_dict=prop)

    def create_batch_of_properties(self, object_type: str, inputs: list):
        return self.hubspot_client.crm.properties.batch_api.create(
            object_type=object_type,
            batch_input_property_create=BatchInputPropertyCreate(inputs=inputs)
        )

    def create_property_group(self, object_type: str, group: dict):
        return self.hubspot_client.crm.properties.groups_api.create(
            object_type=object_type,
            property_group_create=PropertyGroupCreate(**group)
        )

    def get_all_objects(self, object_type: str, properties: list):
        return self.hubspot_client.crm.objects.get_all(object_type=object_type, properties=properties)

    def search(self, object_type: str, properties: list, filters: list, after: str = None):
        return self.hubspot_client.crm.objects.search_api.do_search(
            object_type=object_type,
            public_object_search_request=PublicObjectSearchRequest(
                filter_groups=[
                    {
                        'filters': filters
                    }
                ],
                properties=properties,
                after=after
            )
        )

    def search_records_by_property_with_operator(
        self,
        object_type: str,
        property_name: str,
        operator: str,
        value: Any = None,
        properties: list = None
    ):
        filters = [
            {
                "propertyName": property_name,
                "operator": operator,
                "value": f"{value}"
            }
        ]
        return self.search(object_type=object_type, properties=properties, filters=filters)

    def search_records_updated_since(self, object_type: str, since: int, properties: list):
        return self.search_records_by_property_with_operator(
            object_type=object_type,
            property_name="hs_lastmodifieddate",
            operator="GTE",
            value=since,
            properties=properties
        )

    def search_all_records_with_known_property(
        self,
        object_type: str,
        property_name: int,
        properties: list,
        last_modified_since=None
    ):
        filters = [
            {
                'propertyName': property_name,
                'operator': 'HAS_PROPERTY'
            }
        ]
        if last_modified_since:
            filters.append(
                {
                    'propertyName': 'lastmodifieddate',
                    'operator': 'GTE',
                    'value': str(last_modified_since)
                }
            )
        response = self.search(
            object_type=object_type,
            properties=properties,
            filters=filters
        )
        results = response.results
        after = response.paging.next.after if response.paging else None
        while response.paging:
            response = self.search(
                object_type=object_type,
                properties=properties,
                filters=filters,
                after=after
            )
            after = response.paging.next.after if response.paging else None
            results += response.results
        return results

    def get_associations(self, from_object_type: str, from_object_id: int, to_object_type: str):
        return self.hubspot_client.crm.associations.batch_api.read(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            batch_input_public_object_id=BatchInputPublicObjectId(inputs=[{"id": from_object_id}])
        )

    def get_all_associations_v4(self, from_object_type: str, from_object_id: int, to_object_type: str, after=None):
        batch_request = {
            "inputs": [
                {
                    "id": from_object_id,
                    "after": after
                }
            ]
        }
        associations_response = self.hubspot_client.crm.associations.v4.batch_api.get_page(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            batch_input_public_fetch_associations_batch_request=batch_request
        )
        results = associations_response.results
        for result in associations_response.results:
            while result.paging and result.paging.next and result.paging.next.after:
                results.append(
                    self.get_all_associations_v4(
                        from_object_type=from_object_type,
                        from_object_id=from_object_id,
                        to_object_type=to_object_type,
                        after=result.paging.next.after
                    )
                )
        return results

    def create_associations_batch(
        self,
        from_object_type: str,
        to_object_type: str,
        batch_input_public_association: BatchInputPublicAssociation
    ):
        result = self.hubspot_client.crm.associations.batch_api.create(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            batch_input_public_association=batch_input_public_association
        )
        return result

    def update_objects_batch(self, object_type: str, inputs: List[dict]):
        chunk_size = 100
        results = []
        while inputs:
            chunk, inputs = inputs[:chunk_size], inputs[chunk_size:]

            response = self.hubspot_client.crm.objects.batch_api.update(
                object_type=object_type,
                batch_input_simple_public_object_batch_input={"inputs": list({v['id']: v for v in chunk}.values())}
            )
            results += response.results
        return results

    def create_objects_batch(self, object_type: str, inputs: List[dict]):
        chunk_size = 100
        results = []
        while inputs:
            chunk, inputs = inputs[:chunk_size], inputs[chunk_size:]

            response = self.hubspot_client.crm.objects.batch_api.create(
                object_type=object_type,
                batch_input_simple_public_object_input_for_create={"inputs": chunk}
            )
            results += response.results
        return results

    def delete_objects_batch(self, object_type: str, object_ids: List[int]):
        chunk_size = 100
        while object_ids:
            chunk, object_ids = object_ids[:chunk_size], object_ids[chunk_size:]

            self.hubspot_client.crm.objects.batch_api.archive(
                object_type=object_type,
                batch_input_simple_public_object_id={
                    "inputs": [
                        {
                            "id": object_id
                        } for object_id in chunk
                    ]
                }
            )

    def create_object(
        self,
        object_type: str,
        properties: dict,
        associated_object_id: int = None,
        association_type_id: int = None
    ):
        create_request = {
            "properties": properties
        }
        if associated_object_id and association_type_id:
            create_request['associations'] = [
                {
                    "to": {
                        "id": associated_object_id
                    },
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": association_type_id
                        }
                    ]
                }
            ]
        return self.hubspot_client.crm.objects.basic_api.create(
            object_type=object_type,
            simple_public_object_input_for_create=create_request
        )

    def get_object(self, object_type: str, object_id: int, properties: List[str]):
        return self.hubspot_client.crm.objects.basic_api.get_by_id(
            object_type=object_type,
            object_id=object_id,
            properties=properties
        )

    def update_object(self, object_type: str, object_id: int, properties: dict):
        return self.hubspot_client.crm.objects.basic_api.update(
            object_type=object_type,
            object_id=object_id,
            simple_public_object_input=SimplePublicObjectInput(
                properties=properties
            )
        )

    def merge_objects(self, object_type: str, primary_object_id: int, object_id_to_merge: int):
        return self.hubspot_client.crm.objects.public_object_api.merge(
            object_type=object_type,
            public_merge_input={
                "primaryObjectId": primary_object_id,
                "objectIdToMerge": object_id_to_merge
            }
        )

    def add_attachment(self, object_type: str, object_id: int, file_id: Union[int, str]):
        note_associations = self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
            from_object_type="notes",
            to_object_type=object_type
        )
        association_type = note_associations.results[0].type_id
        note_body = {
            "properties": {
                "hs_attachment_ids": str(file_id),
                "hs_timestamp": f"{datetime.utcnow().isoformat('T', 'milliseconds')}Z"
            },
            "associations": [
                {
                    "to": {
                        "id": str(object_id)
                    },
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": str(association_type)
                        }
                    ]
                }
            ]
        }
        resp = self.hubspot_client.crm.associations.v4.schema.definitions_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/crm/v3/objects/notes",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=note_body
        )
        return json.loads(resp.data)

    def update_associated_objects(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        properties: dict
    ):
        associations = self.get_associations(
            from_object_type=from_object_type,
            from_object_id=from_object_id,
            to_object_type=to_object_type
        )
        inputs = [
            {
                "properties": properties,
                "id": application.id
            } for association in associations.results for application in association.to
        ]
        self.update_objects_batch(object_type=to_object_type, inputs=inputs)

    def copy_associations_to_other_object(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        association_type_map: dict
    ):
        def replace_from_object_id(item, new_id, new_association_type):
            return {
                "from": {
                    "id": new_id
                },
                "to": {
                    "id": item.id
                },
                "type": new_association_type
            }

        for associated_object_type, association_type in association_type_map.items():
            associations_response = self.get_associations(
                from_object_type=from_object_type,
                from_object_id=from_object_id,
                to_object_type=associated_object_type
            )
            if len(associations_response.results) == 0:
                print(f"No associated {associated_object_type} to {from_object_type} {from_object_id}")
                continue
            application_activity_associations = [
                replace_from_object_id(item, to_object_id, association_type)
                for result in associations_response.results for item in result.to
            ]

            self.create_associations_batch(
                from_object_type=to_object_type,
                to_object_type=associated_object_type,
                batch_input_public_association=BatchInputPublicAssociation(inputs=application_activity_associations)
            )

    def get_association_type_id(self, from_object_type: str, to_object_type: str):
        associations = self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
            from_object_type=from_object_type,
            to_object_type=to_object_type
        )
        return associations.results[0].type_id

    def get_association_types(self, from_object_type: str, to_object_type: str):
        return self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
            from_object_type=from_object_type,
            to_object_type=to_object_type
        )

    def get_association_types_as_workflow_options(self, from_object_type: str, to_object_type: str):
        options = []
        if from_object_type and to_object_type:
            association_types = self.get_association_types(
                from_object_type=from_object_type,
                to_object_type=to_object_type
            )
            options = [
                WorkflowFieldOption(
                    label=result.label,
                    description=result.label,
                    value=str(result.type_id)
                ) for result in association_types.results if result.label
            ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=False
        )

    def get_objects_batch(
        self,
        object_type: str,
        ids: Union[List[int], List[str]],
        properties: List[str],
        id_property: str = None
    ):
        chunk_size = 100
        results = []
        while ids:
            chunk, ids = ids[:chunk_size], ids[chunk_size:]
            request = {
                "properties": properties,
                "inputs": [
                    {
                        "id": obj_id
                    } for obj_id in chunk
                ]
            }
            if id_property:
                request['idProperty'] = id_property
            response = self.hubspot_client.crm.objects.batch_api.read(
                object_type=object_type,
                batch_read_input_simple_public_object_id=request
            )
            results += response.results
        return results

    def copy_attachments_to_other_object(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        note_association_type: str
    ):
        def format_association(from_id, to_id, association_type):
            return {
                "from": {
                    "id": from_id
                },
                "to": {
                    "id": to_id
                },
                "type": association_type
            }

        associations_response = self.get_associations(
            from_object_type=from_object_type,
            from_object_id=from_object_id,
            to_object_type="notes"
        )
        notes_response = self.get_objects_batch(
            object_type="notes",
            ids=[item.id for result in associations_response.results for item in result.to],
            properties=["hs_attachment_ids"]
        )
        attachment_associations = [
            format_association(
                from_id=to_object_id,
                to_id=note.id,
                association_type=note_association_type
            ) for note in notes_response if note.properties.get('hs_attachment_ids')
        ]
        if len(attachment_associations) > 0:
            self.create_associations_batch(
                from_object_type=to_object_type,
                to_object_type="notes",
                batch_input_public_association=BatchInputPublicAssociation(inputs=attachment_associations)
            )

    def create_association(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        association_type: str,
    ):
        self.hubspot_client.crm.objects.associations_api.create(
            object_type=from_object_type,
            object_id=from_object_id,
            to_object_type=to_object_type,
            to_object_id=to_object_id,
            association_type=association_type
        )

    def create_association_v4(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        association_category: str,
        association_type_id: int
    ):
        self.hubspot_client.crm.associations.v4.basic_api.create(
            object_type=from_object_type,
            object_id=from_object_id,
            to_object_type=to_object_type,
            to_object_id=to_object_id,
            association_spec=[
                {
                    'associationCategory': association_category,
                    'associationTypeId': association_type_id
                }
            ]
        )

    def associate_object_schemas(self, from_object_type: str, to_object_type: str, label: str, name: str):
        return self.hubspot_client.crm.associations.v4.schema.definitions_api.create(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            public_association_definition_create_request=PublicAssociationDefinitionCreateRequest(
                name=name,
                label=label
            )
        )

    def get_file_by_id(self, file_id):
        return self.hubspot_client.files.files.files_api.get_by_id(file_id=file_id)

    def update_file_properties(self, file, new_file_name: str = None, access: str = None):
        self.hubspot_client.files.files.files_api.update_properties(
            file_id=str(file.id),
            file_update_input={
                "name": new_file_name if new_file_name else file.name,
                "access": access if access else file.access
            }
        )

    def get_file_from_url(self, url: str):
        try:
            response = requests.get(url=url, headers={"Authorization": f"Bearer {self.access_token}"})
            if response.status_code >= 300:
                raise HubSpotFileNotFoundException(
                    status=response.status_code,
                    reason=f"Unable to get file from URL: {response.text}"
                )
            return response.content
        except InvalidSchema:
            link_regex = re.compile(MULTI_URL_REGEX, re.DOTALL)

            for match in link_regex.finditer(url):
                return self.get_file_from_url(url=match.group())

    def get_public_image_files(self, q: str = None, after: str = None):
        params = {
            'sort': ['name'],
            'type': 'IMG',
            'allows_anonymous_access': True
        }
        if q:
            params['name'] = q
        if after:
            params['after'] = after
        return self.hubspot_client.files.files.files_api.do_search(
            **params
        )

    def get_public_images_as_workflow_options(self, q: str = None, after: str = None):
        files_result = self.get_public_image_files(q=q, after=after)
        options = []
        for file in files_result['results']:
            options.append(
                WorkflowFieldOption(
                    label=f"{file['name']}.{file['extension']}",
                    description=file['path'],
                    value=file['url']
                )
            )
        return WorkflowOptionsResponse(
            options=[
                WorkflowFieldOption(
                    label=f"{file['name']}.{file['extension']}",
                    description=file['path'],
                    value=file['url']
                ) for file in files_result.results
            ],
            after=files_result['paging']['next']['after'] if 'paging' in files_result else None,
            searchable=True
        )

    def create_form(self, form_json: dict):
        return self.hubspot_client.marketing.forms.forms_api.create(
            form_json
        )

    def get_form(self, form_id: str):
        return self.hubspot_client.marketing.forms.forms_api.get_by_id(
            form_id=form_id
        )

    def upload_cms_file(self, path: str, file_path: str):
        return self.hubspot_client.cms.source_code.content_api.replace(
            environment="published",
            path=path,
            file=file_path
        )

    def delete_cms_file(self, path: str):
        return self.hubspot_client.cms.source_code.content_api.archive(
            environment="published",
            path=path
        )

    def extract_archive_in_cms(self, path: str):
        return self.hubspot_client.cms.source_code.extract_api.extract_by_path(
            path=path
        )

    def search_files(self, **search_params):
        return self.hubspot_client.files.files.files_api.do_search(**search_params)

    def upload_file(self, file: bytes, options: dict, file_name: str, folder_path: str):
        tmp_path = f"/tmp/{file_name}"
        with open(tmp_path, "wb") as buffer:
            buffer.write(file)
        buffer.close()
        uploaded_file = self.hubspot_client.files.files.files_api.upload(
            file=tmp_path,
            options=json.dumps(options),
            file_name=file_name,
            folder_path=folder_path
        )
        os.remove(tmp_path)
        return uploaded_file

    def get_signed_url_for_file(self, file_id, **kwargs):
        try:
            return self.hubspot_client.files.files.files_api.get_signed_url(file_id=file_id, **kwargs)
        except HubSpotFileNotFoundException:
            return

    def delete_attached_files(self, object_type: str, object_id: int, gdpr_delete: bool = False):
        associations_response = self.get_associations(
            from_object_type=object_type,
            from_object_id=object_id,
            to_object_type="notes"
        )
        notes_response = self.get_objects_batch(
            object_type="notes",
            ids=[item.id for result in associations_response.results for item in result.to],
            properties=["hs_attachment_ids"]
        )
        for note in notes_response:
            file_id = note.properties.get('hs_attachment_ids')
            if file_id:
                if gdpr_delete:
                    self.hubspot_client.files.files.files_api.archive_gdpr(file_id=file_id)
                else:
                    self.hubspot_client.files.files.files_api.archive(file_id=file_id)
                self.hubspot_client.crm.objects.notes.basic_api.archive(note_id=note.id)

    def get_all_folders(self):
        folders = self.hubspot_client.files.files.folders_api.do_search(limit=100).to_dict()
        folder_list = folders['results']
        while folders.get('paging') and folders.get('paging').get('next'):
            folder_list += self.hubspot_client.files.files.folders_api.do_search(
                limit=100,
                after=folders.get('paging').get('next').get('after')
            ).to_dict()['results']

        return sorted(folder_list, key=lambda f: f"{f['path']}/{f['name']}")

    def create_page(self, page: dict):
        resp = self.hubspot_client.cms.domains.domains_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/cms/v3/pages/site-pages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=page
        )
        return json.loads(resp.data)

    def create_list(self, list_json: dict):
        resp = self.hubspot_client.crm.contacts.basic_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/contacts/v1/lists",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=list_json
        )
        return json.loads(resp.data)

    def get_forms(self, after: str = None, limit: int = 100):
        return self.hubspot_client.marketing.forms.forms_api.get_page(limit=limit, after=after)

    def get_forms_as_workflow_options(self, q: str = None, after: str = None):
        forms = self.get_forms(after=after)
        options = [
            WorkflowFieldOption(
                label=form.name,
                description=form.name,
                value=form.id
            ) for form in forms.results if not q or q.lower() in form.name.lower()
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=forms.paging.next.after if forms.paging else None,
            searchable=True
        )

    def upsert_contact(self, properties: dict = None):
        if properties is None:
            return
        simple_public_object_input = SimplePublicObjectInput(
            properties=properties
        )
        if 'email' not in properties:
            return self.hubspot_client.crm.contacts.basic_api.create(
                simple_public_object_input=simple_public_object_input
            )

        search_result = self.hubspot_client.crm.contacts.search_api.do_search(
            public_object_search_request=PublicObjectSearchRequest(
                filter_groups=[
                    {
                        "filters": [
                            {
                                "value": properties.get('email'),
                                "propertyName": "email",
                                "operator": "EQ"
                            }
                        ]
                    }
                ]
            )
        )
        if search_result.total == 0:
            self.hubspot_client.crm.contacts.basic_api.create(
                simple_public_object_input=simple_public_object_input
            )
        else:
            self.hubspot_client.crm.contacts.basic_api.update(
                contact_id=search_result.results[0].id,
                simple_public_object_input=simple_public_object_input
            )

    def get_marketing_events_as_workflow_options(self, q: str = None):
        events = [
            self.get_marketing_event(portal_id=event.external_account_id, external_event_id=event.external_event_id)
            for event in self.get_marketing_events().results
        ]
        options = [
            WorkflowFieldOption(
                label=event.event_name,
                description=event.event_name,
                value=event.id
            ) for event in events if not q or q.lower() in str(event.event_name).lower()
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=None,
            searchable=True
        )

    def get_marketing_events(self, q: str = 'gohsme'):
        return self.hubspot_client.marketing.events.search_api.do_search(q=q)

    def get_marketing_event(self, portal_id: int, external_event_id: str):
        return self.hubspot_client.marketing.events.marketing_events_external_api.get_by_id(
            external_event_id=external_event_id,
            external_account_id=str(portal_id)
        )

    def create_marketing_event(self, marketing_event_create_request: MarketingEvent):
        return self.hubspot_client.marketing.events.marketing_events_external_api.create(
            marketing_event_create_request_params=marketing_event_create_request.model_dump(
                by_alias=True,
                exclude_unset=True,
                exclude_none=True
            )
        )

    def update_marketing_event_subscriber_state(
        self,
        portal_id: int,
        external_event_id: str,
        contact_id: int,
        subscriber_state: str,
        timestamp: int
    ):
        try:
            return self.hubspot_client.marketing.events.attendance_subscriber_state_changes_api.create(
                external_event_id=external_event_id,
                subscriber_state=subscriber_state,
                batch_input_marketing_event_subscriber=BatchInputMarketingEventSubscriber(
                    inputs=[
                        {
                            "vid": contact_id,
                            "interactionDateTime": timestamp
                        }
                    ]
                ),
                external_account_id=str(portal_id)
            )
        except hubspot.marketing.events.exceptions.ApiException as e:
            if 'Error: (429)' in str(e):
                raise
            self.logger.log_text(
                f"Marketing Event {external_event_id} does not exist for portal {portal_id}. Error: {str(e)}",
                severity="DEBUG"
            )
            raise HubSpotWorkflowException(
                error_code=ErrorCode.INVALID_EVENT,
                message=f"Marketing Event {external_event_id} does not exist for portal {portal_id}"
            )

    def complete_blocked_workflow_execution(
        self,
        callback_id: str,
        workflow_action_output: dict
    ):
        self.hubspot_client.automation.actions.callbacks_api.complete(
            callback_id=callback_id,
            callback_completion_request=workflow_action_output
        )

    def complete_blocked_workflow_executions_for_callback_ids_list(
        self,
        callback_ids: List[str],
        output_data: Any = None
    ):
        chunk_size = 100
        while callback_ids:
            chunk, callback_ids = callback_ids[:chunk_size], callback_ids[chunk_size:]
            output_fields = {
                "hs_execution_state": HubSpotExecutionState.SUCCESS
            }
            if type(output_data) == dict:
                output_fields |= output_data
            data = HubSpotWorkflowActionCallbackBatchModel(
                inputs=[
                    HubSpotWorkflowActionCallbackModel(
                        output_fields=HubSpotWorkflowActionOutputFieldsModel(**output_fields),
                        callback_id=callback_id
                    ) for callback_id in set(chunk)
                ]
            ).model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
            self.hubspot_client.automation.actions.callbacks_api.complete_batch(
                batch_input_callback_completion_batch_request=data
            )

    def get_products(self, after: str = None, limit: int = 100):
        return self.hubspot_client.crm.products.basic_api.get_page(limit=limit, after=after)

    def get_products_as_workflow_options(self, q: str = None, after: str = None):
        products = self.get_products(after=after)
        options = [
            WorkflowFieldOption(
                label=product.properties['name'],
                description=product.properties['name'],
                value=product.id
            ) for product in products.results if not q or q.lower() in product.properties['name'].lower()
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=products.paging.next.after if products.paging else None,
            searchable=True
        )

    def create_timeline_event(
        self,
        timeline_event: TimelineEvent
    ):
        return self.hubspot_client.crm.timeline.events_api.create(
            timeline_event=timeline_event.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        )

    def create_timeline_events(self, inputs: List[TimelineEvent]):
        return self.hubspot_client.crm.timeline.events_api.create_batch(
            batch_input_timeline_event={
                'inputs': [
                    timeline_event.model_dump(
                        by_alias=True,
                        exclude_unset=True,
                        exclude_none=True
                    ) for timeline_event in inputs
                ]
            }
        )

    def get_subscription_types(self):
        return self.hubspot_client.communication_preferences.definition_api.get_page()

    def get_subscription_statuses(self, email: str):
        return self.hubspot_client.communication_preferences.status_api.get_email_status(
            email_address=email
        )

    def subscribe_contact(
        self,
        email: str,
        subscription_id: str,
        legal_basis: str,
        legal_basis_explanation: str
    ):
        data = {
            'emailAddress': email,
            'subscriptionId': subscription_id,
            'legalBasis': legal_basis,
            'legalBasisExplanation': legal_basis_explanation
        }
        return self.hubspot_client.communication_preferences.status_api.subscribe(
            public_update_subscription_status_request=data
        )

    def unsubscribe_contact(
        self,
        email: str,
        subscription_id: str,
        legal_basis: str,
        legal_basis_explanation: str
    ):
        data = {
            'emailAddress': email,
            'subscriptionId': subscription_id,
            'legalBasis': legal_basis,
            'legalBasisExplanation': legal_basis_explanation
        }
        return self.hubspot_client.communication_preferences.status_api.unsubscribe(
            public_update_subscription_status_request=data
        )
