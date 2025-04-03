import json
import os
import re
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from functools import cached_property
from typing import Any, List, Union

import requests
from hubspot import HubSpot
from hubspot.automation.actions import ApiException as AutomationException
from hubspot.cms.source_code import ActionResponse
from hubspot.crm.associations import (
    BatchInputPublicAssociation,
    BatchInputPublicObjectId,
)
from hubspot.crm.associations.v4.schema import PublicAssociationDefinitionCreateRequest
from hubspot.crm.lists import ListCreateResponse
from hubspot.crm.objects import PublicObjectSearchRequest, SimplePublicObjectInput
from hubspot.crm.properties import BatchInputPropertyCreate, Option, PropertyGroupCreate
from hubspot.crm.schemas import ObjectSchema
from hubspot.files.exceptions import NotFoundException as HubSpotFileNotFoundException
from hubspot.marketing.events import (
    BatchInputMarketingEventSubscriber,
    CollectionResponseWithTotalParticipationBreakdownForwardPaging,
    MarketingEventAssociation,
    ParticipationAssociations,
    ParticipationBreakdown,
    ParticipationProperties,
)
from hubspot.marketing.events.exceptions import ApiException as MarketingEventsException
from requests.exceptions import InvalidSchema
from urllib3.util.retry import Retry

from common.core.utils import merge_dicts_of_lists, timed_lru_cache
from common.models.hubspot.files import File
from common.models.hubspot.marketing_events import (
    MarketingEvent,
    MarketingEventResultsWithPaging,
    SubscriberState,
)
from common.models.hubspot.settings import HubSpotAccountDetails
from common.models.hubspot.timeline_events import TimelineEvent
from common.models.hubspot.workflow_actions import (
    ActionOutputFields,
    ErrorCode,
    ExecutionState,
    FileAccess,
    FileDeletionType,
    FileSource,
    FileType,
    HubSpotWorkflowException,
    WorkflowActionCallback,
    WorkflowActionCallbackBatch,
    WorkflowFieldOption,
    WorkflowOptionsResponse,
)
from common.services import constants
from common.services.base import BaseService

MULTI_URL_REGEX = r"((https?):((//)|(\\\\))+([\w\d:#@%/;$~_?\+-=\\\.&](#!)?)*)"


class HubSpotService(BaseService):
    base_url = "https://api.hubapi.com"

    def __init__(
        self,
        access_token: str = None,
        api_key: str = None,
    ) -> None:
        self.access_token = access_token
        self.api_key = api_key
        retry = Retry(
            total=60,
            backoff_factor=10,
            status_forcelist=(429, 502, 504),
        )
        self.hubspot_client = HubSpot(
            access_token=access_token,
            api_key=api_key,
            retry=retry,
        )
        super().__init__(
            log_name="hubspot.service",
        )

    def get_account_details(self) -> HubSpotAccountDetails:
        resp = self.hubspot_client.oauth.access_tokens_api.api_client.request(
            method="GET",
            url="https://api.hubapi.com/account-info/v3/details",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return HubSpotAccountDetails.model_validate(json.loads(resp.data))

    def get_token_details(self):
        return self.hubspot_client.oauth.access_tokens_api.get(self.access_token)

    def get_authed_user(self):
        return self.get_user(user_id=self.get_token_details().user_id)

    def get_user(self, user_id):
        return self.get_owner_by_id(owner_id=user_id, id_property="userId")

    def get_users(self):
        users_response = self.hubspot_client.settings.users.users_api.get_page()
        users = users_response.results
        while (
            users_response.paging
            and users_response.paging.next
            and users_response.paging.next.after
        ):
            users_response = self.hubspot_client.settings.users.users_api.get_page(
                after=users_response.paging.next.after
            )
            users += users_response.results
        return users

    def get_owner_by_id(self, owner_id, id_property: str = "id"):
        return self.hubspot_client.crm.owners.owners_api.get_by_id(
            owner_id, id_property=id_property
        )

    def get_owners(self, archived: bool = False):
        owners_response = self.hubspot_client.crm.owners.owners_api.get_page(
            archived=archived
        )
        owners = owners_response.results
        while (
            owners_response.paging
            and owners_response.paging.next
            and owners_response.paging.next.after
        ):
            owners_response = self.hubspot_client.crm.owners.owners_api.get_page(
                after=owners_response.paging.next.after, archived=archived
            )
            owners += owners_response.results
        if archived:
            users_by_email = {user.email: user for user in self.get_users()}
            for owner in owners:
                user = users_by_email.get(owner.email)
                if not user:
                    owner.teams = []
                    continue
                teams = []
                if user.primary_team_id:
                    teams.append({"id": user.primary_team_id, "primary": True})
                if user.secondary_team_ids:
                    teams += [
                        {"id": team_id, "primary": False}
                        for team_id in user.secondary_team_ids
                    ]
                owner.teams = teams
                owner.user_id = user.id
        return owners

    def get_owners_as_workflow_options(
        self, include_deactivated: bool = False
    ) -> WorkflowOptionsResponse:
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
                value=owner.id,
            )
            for owner in sorted(owners, key=lambda o: o.email)
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def revoke(self):
        token_details = self.get_token_details()
        application_name = {v["app_id"]: k for k, v in self.config["apps"].items()}[
            token_details.app_id
        ]
        token = self.firestore_service.get_account_connection(
            app_name=application_name, account_id=token_details.hub_id
        )
        self.hubspot_client.oauth.refresh_tokens_api.archive(token.refresh_token)

    @timed_lru_cache(seconds=3600)
    def get_team(self, team_id: str):
        for team in self.get_teams:
            if team.id == team_id:
                return team

    @cached_property
    def get_teams(self):
        return self.hubspot_client.settings.users.teams_api.get_all().results

    @cached_property
    def get_teams_as_workflow_options(self) -> WorkflowOptionsResponse:
        teams = self.get_teams
        options = [
            WorkflowFieldOption(label=team.name, description=team.name, value=team.id)
            for team in sorted(teams, key=lambda t: t.name)
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def get_custom_workflow_actions(self, app_id: int):
        return self.hubspot_client.automation.actions.definitions_api.get_page(
            app_id=app_id
        )

    def create_workflow(self, workflow: dict):
        resp = self.hubspot_client.crm.associations.v4.schema.definitions_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/automation/v4/flows",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=workflow,
        )
        return json.loads(resp.data)

    def create_custom_object(self, object_schema: dict) -> ObjectSchema:
        return self.hubspot_client.crm.schemas.core_api.create(
            object_schema_egg=object_schema
        )

    def get_custom_object(self, object_type: str) -> ObjectSchema:
        return self.hubspot_client.crm.schemas.core_api.get_by_id(
            object_type=object_type
        )

    def create_pipeline(self, object_type: str, pipeline: dict):
        return self.hubspot_client.crm.pipelines.pipelines_api.create(
            object_type=object_type, pipeline_input=pipeline
        )

    def get_pipeline_stages(self, object_type: str, pipeline_id: str):
        return self.hubspot_client.crm.pipelines.pipeline_stages_api.get_all(
            object_type=object_type, pipeline_id=pipeline_id
        )

    @cached_property
    def get_objects_as_workflow_options(self) -> WorkflowOptionsResponse:
        objects = constants.BASE_WORKFLOW_ACTION_OBJECTS
        if "crm.schemas.custom.read" in self.get_token_details().scopes:
            for (
                custom_object
            ) in self.hubspot_client.crm.schemas.core_api.get_all().results:
                objects.append(
                    {
                        "label": custom_object.labels.singular,
                        "value": custom_object.object_type_id,
                    }
                )
        unique_objects = list({v["value"]: v for v in objects}.values())
        options = [
            WorkflowFieldOption(
                label=obj["label"], description=obj["label"], value=obj["value"]
            )
            for obj in unique_objects
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    @cached_property
    def get_all_object_types(self):
        objects = constants.BASE_OBJECT_TYPES
        if "crm.schemas.custom.read" in self.get_token_details().scopes:
            for (
                custom_object
            ) in self.hubspot_client.crm.schemas.core_api.get_all().results:
                objects.append(
                    {
                        "label": custom_object.labels.singular,
                        "value": custom_object.object_type_id,
                    }
                )
        unique_objects = list({v["value"]: v for v in objects}.values())
        options = [
            WorkflowFieldOption(
                label=obj["label"], description=obj["label"], value=obj["value"]
            )
            for obj in unique_objects
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def get_properties_as_workflow_options(
        self,
        object_type: str,
        field_type: str = None,
        referenced_object_type: str = None,
        modifiable: bool = None,
        exclude: List[str] = None,
        include: List[str] = None,
    ) -> WorkflowOptionsResponse:
        properties = self.get_all_properties(object_type=object_type)
        if field_type:
            options = [
                WorkflowFieldOption(
                    label=prop.label, description=prop.description, value=prop.name
                )
                for prop in properties.results
                if (
                    prop.field_type == field_type
                    and (
                        modifiable is None
                        or (
                            prop.modification_metadata.read_only_value != modifiable
                            and not prop.external_options
                        )
                    )
                    and (not exclude or prop.name not in exclude)
                )
                or (include and prop.name in include)
            ]
        elif referenced_object_type:
            options = [
                WorkflowFieldOption(
                    label=prop.label, description=prop.label, value=prop.name
                )
                for prop in properties.results
                if (
                    prop.referenced_object_type == referenced_object_type
                    and (
                        modifiable is None
                        or prop.modification_metadata.read_only_value != modifiable
                    )
                    and (not exclude or prop.name not in exclude)
                )
                or (include and prop.name in include)
            ]
        else:
            options = [
                WorkflowFieldOption(
                    label=prop.label, description=prop.label, value=prop.name
                )
                for prop in properties.results
                if (
                    (
                        modifiable is None
                        or prop.modification_metadata.read_only_value != modifiable
                    )
                    and (not exclude or prop.name not in exclude)
                )
                or (include and prop.name in include)
            ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def get_properties_by_field_types(
        self,
        object_type: str,
        field_types: List[str] = None,
        modifiable: bool = None,
        exclude: List[str] = None,
        exclude_reference_object_types: List[str] = None,
    ):
        properties = self.get_all_properties(object_type=object_type).to_dict()
        options = (
            [
                prop
                for prop in properties["results"]
                if (not field_types or prop["field_type"] in field_types)
                and (
                    modifiable is None
                    or prop["modification_metadata"]["read_only_value"] != modifiable
                )
                and (not exclude or prop["name"] not in exclude)
                and (
                    not exclude_reference_object_types
                    or not prop.get("referenced_object_type")
                    or prop.get("referenced_object_type")
                    not in exclude_reference_object_types
                )
            ]
            if field_types
            else properties["results"]
        )
        return options

    def get_pipeline_stages_as_workflow_options(
        self, object_type: str, pipeline_id: str
    ) -> WorkflowOptionsResponse:
        stages = self.get_pipeline_stages(
            object_type=object_type, pipeline_id=pipeline_id
        )
        options = [
            WorkflowFieldOption(
                label=stage.label, description=stage.label, value=stage.id
            )
            for stage in stages.results
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def get_pipelines(self, object_type: str):
        return self.hubspot_client.crm.pipelines.pipelines_api.get_all(
            object_type=object_type
        )

    def get_pipelines_as_workflow_options(
        self, object_type: str
    ) -> WorkflowOptionsResponse:
        pipelines = self.get_pipelines(object_type=object_type)
        options = [
            WorkflowFieldOption(
                label=pipeline.label, description=pipeline.label, value=pipeline.id
            )
            for pipeline in pipelines.results
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def create_property(self, object_type: str, property_dict: dict):
        return self.hubspot_client.crm.properties.core_api.create(
            object_type=object_type, property_create=property_dict
        )

    def get_property(self, object_type: str, property_name: str):
        return self.hubspot_client.crm.properties.core_api.get_by_name(
            object_type=object_type, property_name=property_name
        )

    def get_portal_currency_options(self) -> List[Option]:
        account_details = self.get_account_details()
        currencies = [
            Option(
                label=account_details.company_currency,
                value=account_details.company_currency,
            )
        ]
        if account_details.additional_currencies:
            currencies += [
                Option(label=currency, value=currency)
                for currency in account_details.additional_currencies
            ]

        return currencies

    @timed_lru_cache(seconds=3600)
    def get_property_options_as_workflow_options(
        self, object_type: str, property_name: str, q: str = None
    ) -> WorkflowOptionsResponse:
        prop = self.get_property(object_type=object_type, property_name=property_name)
        property_options = prop.options
        option_values_function_map = {
            "line_item:hs_line_item_currency_code": self.get_portal_currency_options
        }
        property_options_function = option_values_function_map.get(
            f"{object_type}:{property_name}".lower()
        )
        if property_options_function:
            property_options = property_options_function()
        options = [
            WorkflowFieldOption(label=option.label, value=option.value)
            for option in property_options
            if not q
            or q.lower() in option.label.lower()
            or q.lower() in option.value.lower()
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=True)

    def get_all_properties(self, object_type: str):
        return self.hubspot_client.crm.properties.core_api.get_all(
            object_type=object_type
        )

    def update_property(
        self, object_type: str, property_name: str, property_dict: dict
    ):
        return self.hubspot_client.crm.properties.core_api.update(
            object_type=object_type,
            property_name=property_name,
            property_update=property_dict,
        )

    def merge_property_options(
        self,
        object_type: str,
        property_name: str,
        new_options: List[dict],
        option_value_key: str = "value",
        option_label_key: str = "label",
    ):
        def parse_option(index, option):
            return {
                "display_order": index + 1,
                "hidden": False,
                "label": str(option[option_label_key]),
                "value": str(option[option_value_key]),
            }

        prop = self.get_property(
            object_type=object_type, property_name=property_name
        ).to_dict()
        new_option_map = {
            o[option_value_key]: parse_option(i, o) for i, o in enumerate(new_options)
        }
        for o in prop["options"]:
            if o["value"] and len(o["value"]) > 0 and o["value"] not in new_option_map:
                new_option_map[o["value"]] = o
        if not new_option_map:
            print(
                f"Unable to update property {object_type}.{property_name}. At least one option is required."
            )
            return
        prop["options"] = list(new_option_map.values())
        return self.update_property(
            object_type=object_type, property_name=property_name, property_dict=prop
        )

    def create_batch_of_properties(self, object_type: str, inputs: list):
        return self.hubspot_client.crm.properties.batch_api.create(
            object_type=object_type,
            batch_input_property_create=BatchInputPropertyCreate(inputs=inputs),
        )

    def create_property_group(self, object_type: str, group: dict):
        return self.hubspot_client.crm.properties.groups_api.create(
            object_type=object_type, property_group_create=PropertyGroupCreate(**group)
        )

    def get_all_objects(self, object_type: str, properties: list):
        return self.hubspot_client.crm.objects.get_all(
            object_type=object_type, properties=properties
        )

    def search(
        self, object_type: str, properties: list, filters: list, after: str = None
    ):
        return self.hubspot_client.crm.objects.search_api.do_search(
            object_type=object_type,
            public_object_search_request=PublicObjectSearchRequest(
                filter_groups=[{"filters": filters}], properties=properties, after=after
            ),
        )

    def search_records_by_property_with_operator(
        self,
        object_type: str,
        property_name: str,
        operator: str,
        value: Any = None,
        properties: list = None,
    ):
        filters = [
            {"propertyName": property_name, "operator": operator, "value": f"{value}"}
        ]
        return self.search(
            object_type=object_type, properties=properties, filters=filters
        )

    def search_records_updated_since(
        self, object_type: str, since: int, properties: list
    ):
        return self.search_records_by_property_with_operator(
            object_type=object_type,
            property_name="hs_lastmodifieddate",
            operator="GTE",
            value=since,
            properties=properties,
        )

    def search_all_records_with_known_property(
        self,
        object_type: str,
        property_name: int,
        properties: list,
        last_modified_since=None,
    ):
        filters = [{"propertyName": property_name, "operator": "HAS_PROPERTY"}]
        if last_modified_since:
            filters.append(
                {
                    "propertyName": "lastmodifieddate",
                    "operator": "GTE",
                    "value": str(last_modified_since),
                }
            )
        response = self.search(
            object_type=object_type, properties=properties, filters=filters
        )
        results = response.results
        after = response.paging.next.after if response.paging else None
        while response.paging:
            response = self.search(
                object_type=object_type,
                properties=properties,
                filters=filters,
                after=after,
            )
            after = response.paging.next.after if response.paging else None
            results += response.results
        return results

    def get_associations(
        self, from_object_type: str, from_object_id: int, to_object_type: str
    ):
        return self.hubspot_client.crm.associations.batch_api.read(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            batch_input_public_object_id=BatchInputPublicObjectId(
                inputs=[{"id": from_object_id}]
            ),
        )

    def get_all_associations_v4(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        after=None,
    ):
        batch_request = {"inputs": [{"id": from_object_id, "after": after}]}
        associations_response = (
            self.hubspot_client.crm.associations.v4.batch_api.get_page(
                from_object_type=from_object_type,
                to_object_type=to_object_type,
                batch_input_public_fetch_associations_batch_request=batch_request,
            )
        )
        results = associations_response.results
        for result in associations_response.results:
            while result.paging and result.paging.next and result.paging.next.after:
                results.append(
                    self.get_all_associations_v4(
                        from_object_type=from_object_type,
                        from_object_id=from_object_id,
                        to_object_type=to_object_type,
                        after=result.paging.next.after,
                    )
                )
        return results

    def get_all_associations_batch(
        self, from_object_type: str, inputs: List[dict], to_object_type: str
    ):
        """
        :param from_object_type: str
        :param inputs: [{'id': int, 'after': str}]
        :param to_object_type: str
        """
        batch_request = {"inputs": inputs}
        associations_response = (
            self.hubspot_client.crm.associations.v4.batch_api.get_page(
                from_object_type=from_object_type,
                to_object_type=to_object_type,
                batch_input_public_fetch_associations_batch_request=batch_request,
            )
        )
        results = defaultdict(list)
        new_inputs = []
        for result in associations_response.results:
            results[result._from.id] += result.to
            if result.paging and result.paging.next and result.paging.next.after:
                new_inputs.append(
                    {"id": result._from.id, "after": result.paging.next.after}
                )
        if new_inputs:
            results = merge_dicts_of_lists(
                dict1=results,
                dict2=self.get_all_associations_batch(
                    from_object_type=from_object_type,
                    inputs=new_inputs,
                    to_object_type=to_object_type,
                ),
            )
        return results

    def create_associations_batch(
        self,
        from_object_type: str,
        to_object_type: str,
        batch_input_public_association: BatchInputPublicAssociation,
    ):
        result = self.hubspot_client.crm.associations.batch_api.create(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            batch_input_public_association=batch_input_public_association,
        )
        return result

    def update_objects_batch(self, object_type: str, inputs: List[dict]):
        chunk_size = 100
        results = []
        while inputs:
            chunk, inputs = inputs[:chunk_size], inputs[chunk_size:]

            response = self.hubspot_client.crm.objects.batch_api.update(
                object_type=object_type,
                batch_input_simple_public_object_batch_input={
                    "inputs": list({v["id"]: v for v in chunk}.values())
                },
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
                batch_input_simple_public_object_input_for_create={"inputs": chunk},
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
                    "inputs": [{"id": object_id} for object_id in chunk]
                },
            )

    def create_object(
        self,
        object_type: str,
        properties: dict,
        associated_object_id: int = None,
        association_type_id: int = None,
    ):
        create_request = {"properties": properties}
        if associated_object_id and association_type_id:
            create_request["associations"] = [
                {
                    "to": {"id": associated_object_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": association_type_id,
                        }
                    ],
                }
            ]
        return self.hubspot_client.crm.objects.basic_api.create(
            object_type=object_type,
            simple_public_object_input_for_create=create_request,
        )

    def get_object(self, object_type: str, object_id: int, properties: List[str]):
        return self.hubspot_client.crm.objects.basic_api.get_by_id(
            object_type=object_type, object_id=object_id, properties=properties
        )

    def update_object(self, object_type: str, object_id: int, properties: dict):
        return self.hubspot_client.crm.objects.basic_api.update(
            object_type=object_type,
            object_id=object_id,
            simple_public_object_input=SimplePublicObjectInput(properties=properties),
        )

    def merge_objects(
        self, object_type: str, primary_object_id: int, object_id_to_merge: int
    ):
        if object_type == "CONTACT":
            return self.hubspot_client.crm.contacts.merge_api.merge(
                public_merge_input={
                    "primaryObjectId": primary_object_id,
                    "objectIdToMerge": object_id_to_merge,
                }
            )
        elif object_type == "COMPANY":
            return self.hubspot_client.crm.companies.merge_api.merge(
                public_merge_input={
                    "primaryObjectId": primary_object_id,
                    "objectIdToMerge": object_id_to_merge,
                }
            )
        elif object_type == "DEAL":
            return self.hubspot_client.crm.deals.merge_api.merge(
                public_merge_input={
                    "primaryObjectId": primary_object_id,
                    "objectIdToMerge": object_id_to_merge,
                }
            )
        else:
            raise ValueError(f"Object type {object_type} not supported for merge")

    def add_attachment(
        self, object_type: str, object_id: int, file_id: Union[int, str]
    ):
        note_association_types = (
            self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
                from_object_type="notes", to_object_type=object_type
            )
        )
        note_associations = self.get_all_associations_v4(
            from_object_type=object_type,
            from_object_id=object_id,
            to_object_type="notes",
        )
        notes = self.get_objects_batch(
            object_type="notes",
            ids=[
                obj.to_object_id
                for association in note_associations
                for obj in association.to
            ],
            properties=["hs_attachment_ids"],
        )

        # check to see if the file is already associated with the object
        for note in notes:
            if note.properties.get("hs_attachment_ids") and str(
                file_id
            ) in note.properties.get("hs_attachment_ids"):
                return note

        association_type = note_association_types.results[0]
        note_body = {
            "properties": {
                "hs_attachment_ids": str(file_id),
                "hs_timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            },
            "associations": [
                {
                    "to": {"id": str(object_id)},
                    "types": [
                        {
                            "associationCategory": association_type.category,
                            "associationTypeId": str(association_type.type_id),
                        }
                    ],
                }
            ],
        }
        resp = self.hubspot_client.crm.associations.v4.schema.definitions_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/crm/v3/objects/notes",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=note_body,
        )
        return json.loads(resp.data)

    def update_associated_objects(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        properties: dict,
    ):
        associations = self.get_associations(
            from_object_type=from_object_type,
            from_object_id=from_object_id,
            to_object_type=to_object_type,
        )
        inputs = [
            {"properties": properties, "id": application.id}
            for association in associations.results
            for application in association.to
        ]
        self.update_objects_batch(object_type=to_object_type, inputs=inputs)

    def copy_associations_to_other_object(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        association_type_map: dict,
    ):
        def replace_from_object_id(item, new_id, new_association_type):
            return {
                "from": {"id": new_id},
                "to": {"id": item.id},
                "type": new_association_type,
            }

        for associated_object_type, association_type in association_type_map.items():
            associations_response = self.get_associations(
                from_object_type=from_object_type,
                from_object_id=from_object_id,
                to_object_type=associated_object_type,
            )
            if len(associations_response.results) == 0:
                print(
                    f"No associated {associated_object_type} to {from_object_type} {from_object_id}"
                )
                continue
            application_activity_associations = [
                replace_from_object_id(item, to_object_id, association_type)
                for result in associations_response.results
                for item in result.to
            ]

            self.create_associations_batch(
                from_object_type=to_object_type,
                to_object_type=associated_object_type,
                batch_input_public_association=BatchInputPublicAssociation(
                    inputs=application_activity_associations
                ),
            )

    def get_association_type_id(self, from_object_type: str, to_object_type: str):
        association_type = self.get_association_type(
            from_object_type=from_object_type, to_object_type=to_object_type
        )
        return association_type.type_id if association_type else None

    def get_association_type(self, from_object_type: str, to_object_type: str):
        associations = (
            self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
                from_object_type=from_object_type, to_object_type=to_object_type
            )
        )
        return associations.results[0] if associations.results else None

    def get_association_types(self, from_object_type: str, to_object_type: str):
        return self.hubspot_client.crm.associations.v4.schema.definitions_api.get_all(
            from_object_type=from_object_type, to_object_type=to_object_type
        )

    def get_association_types_as_workflow_options(
        self, from_object_type: str, to_object_type: str
    ) -> WorkflowOptionsResponse:
        options = []
        if from_object_type and to_object_type:
            association_types = self.get_association_types(
                from_object_type=from_object_type, to_object_type=to_object_type
            )
            options = [
                WorkflowFieldOption(
                    label=result.label,
                    description=result.label,
                    value=str(result.type_id),
                )
                for result in association_types.results
                if result.label
            ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=False)

    def get_objects_batch(
        self,
        object_type: str,
        ids: Union[List[int], List[str]],
        properties: List[str],
        id_property: str = None,
    ):
        chunk_size = 100
        results = []
        while ids:
            chunk, ids = ids[:chunk_size], ids[chunk_size:]
            request = {
                "properties": properties,
                "inputs": [{"id": obj_id} for obj_id in chunk],
            }
            if id_property:
                request["idProperty"] = id_property
            response = self.hubspot_client.crm.objects.batch_api.read(
                object_type=object_type,
                batch_read_input_simple_public_object_id=request,
            )
            results += response.results
        return results

    def create_association(
        self,
        from_object_type: str,
        from_object_id: int,
        to_object_type: str,
        to_object_id: int,
        association_category: str = None,
        association_type_id: int = None,
    ):
        if not association_category or not association_type_id:
            association_type = self.get_association_type(
                from_object_type=from_object_type, to_object_type=to_object_type
            )
            association_category = (
                association_type.category
                if not association_category
                else association_category
            )
            association_type_id = (
                association_type.type_id
                if not association_type_id
                else association_type_id
            )
        self.hubspot_client.crm.associations.v4.basic_api.create(
            object_type=from_object_type,
            object_id=from_object_id,
            to_object_type=to_object_type,
            to_object_id=to_object_id,
            association_spec=[
                {
                    "associationCategory": association_category,
                    "associationTypeId": association_type_id,
                }
            ],
        )

    def associate_object_schemas(
        self, from_object_type: str, to_object_type: str, label: str, name: str
    ):
        return self.hubspot_client.crm.associations.v4.schema.definitions_api.create(
            from_object_type=from_object_type,
            to_object_type=to_object_type,
            public_association_definition_create_request=PublicAssociationDefinitionCreateRequest(
                name=name, label=label
            ),
        )

    def get_file_by_id(self, file_id) -> File:
        data = self.hubspot_client.files.files_api.get_by_id(file_id=file_id)
        return File.model_validate(data.to_dict())

    def update_file_properties(
        self, file, new_file_name: str = None, access: FileAccess = None
    ):
        file_update_input = {}
        if new_file_name:
            file_update_input["name"] = new_file_name
        if access:
            file_update_input["access"] = access.value
        self.hubspot_client.files.files_api.update_properties(
            file_id=str(file.id), file_update_input=file_update_input
        )

    def get_file_from_url(self, url: str):
        try:
            response = requests.get(
                url=url, headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if response.status_code >= 300:
                raise HubSpotFileNotFoundException(
                    status=response.status_code,
                    reason=f"Unable to get file from URL: {response.text}",
                )
            return response.content
        except InvalidSchema:
            link_regex = re.compile(MULTI_URL_REGEX, re.DOTALL)

            for match in link_regex.finditer(url):
                return self.get_file_from_url(url=match.group())

    def get_public_image_files(self, q: str = None, after: str = None):
        params = {"sort": ["name"], "type": "IMG", "allows_anonymous_access": True}
        if q:
            params["name"] = q
        if after:
            params["after"] = after
        return self.hubspot_client.files.files_api.do_search(**params)

    def get_public_images_as_workflow_options(
        self, q: str = None, after: str = None
    ) -> WorkflowOptionsResponse:
        files_result = self.get_public_image_files(q=q, after=after)
        return WorkflowOptionsResponse(
            options=[
                WorkflowFieldOption(
                    label=f"{file.name}.{file.extension}",
                    description=file.path,
                    value=file.url,
                )
                for file in files_result.results
            ],
            after=files_result.paging.next.after
            if files_result.paging and files_result.paging.next
            else None,
            searchable=True,
        )

    def create_form(self, form_json: dict):
        return self.hubspot_client.marketing.forms.forms_api.create(form_json)

    def get_form(self, form_id: str):
        return self.hubspot_client.marketing.forms.forms_api.get_by_id(form_id=form_id)

    def upload_cms_file(self, path: str, file_path: str):
        return self.hubspot_client.cms.source_code.content_api.create_or_update(
            environment="published", path=path, file=file_path
        )

    def delete_cms_file(self, path: str):
        return self.hubspot_client.cms.source_code.content_api.archive(
            environment="published", path=path
        )

    def extract_archive_in_cms(self, path: str) -> ActionResponse:
        task = self.hubspot_client.cms.source_code.extract_api.do_async(
            file_extract_request={"path": path}
        )
        while True:
            action_response = (
                self.hubspot_client.cms.source_code.extract_api.get_async_status(
                    task_id=task.id
                )
            )
            if action_response.status == "CANCELED":
                raise Exception("Extract task was canceled")
            if action_response.status == "COMPLETE":
                return action_response

    def search_files(self, **search_params):
        return self.hubspot_client.files.files_api.do_search(**search_params)

    def upload_file(self, file: bytes, options: dict, file_name: str, folder_path: str):
        tmp_path = f"/tmp/{file_name}"
        with open(tmp_path, "wb") as buffer:
            buffer.write(file)
        buffer.close()
        uploaded_file = self.hubspot_client.files.files_api.upload(
            file=tmp_path,
            options=json.dumps(options),
            file_name=file_name,
            folder_path=folder_path,
        )
        os.remove(tmp_path)
        return uploaded_file

    def get_signed_url_for_file(self, file_id, **kwargs):
        try:
            return self.hubspot_client.files.files_api.get_signed_url(
                file_id=file_id, **kwargs
            )
        except HubSpotFileNotFoundException:
            return

    def delete_attached_files(
        self,
        object_type: str,
        object_id: int,
        deletion_type: FileDeletionType,
        file_source: FileSource = None,
        file_type: FileType = None,
    ):
        engagement_association_type = self.get_association_type_id(
            from_object_type=object_type, to_object_type="engagements"
        )
        engagement_object_type = (
            "engagements" if engagement_association_type else "notes"
        )
        associations_response = self.get_associations(
            from_object_type=object_type,
            from_object_id=object_id,
            to_object_type=engagement_object_type,
        )
        engagements_response = self.get_objects_batch(
            object_type=engagement_object_type,
            ids=[
                item.id
                for result in associations_response.results
                for item in result.to
            ],
            properties=[
                "hs_attachment_ids",
                "hs_engagement_type",
                "hs_engagement_source",
            ],
        )
        attachments = [
            engagement
            for engagement in engagements_response
            if engagement.properties.get("hs_attachment_ids")
            and (
                not file_source
                or (
                    file_source == FileSource.MANUAL_UPLOAD
                    and engagement.properties.get("hs_engagement_source") == "CRM_UI"
                )
                or file_source.value in engagement.properties.get("hs_engagement_type")
            )
        ]
        if len(attachments) == 0:
            return
        associations_to_delete = []
        engagements_to_update_by_type = defaultdict(list)
        for attachment in attachments:
            engagement_type = (
                attachment.properties.get("hs_engagement_type")
                .replace("INCOMING_EMAIL", "EMAIL")
                .replace("FORWARDED_EMAIL", "EMAIL")
            )
            deleted_attachments = []
            attachment_ids = attachment.properties.get("hs_attachment_ids").split(";")
            for file_id in attachment_ids:
                if not file_id:
                    continue
                try:
                    file = self.get_file_by_id(file_id=file_id)
                except HubSpotFileNotFoundException:
                    if engagement_type == "NOTE":
                        associations_to_delete.append({"id": attachment.id})
                    else:
                        deleted_attachments.append(file_id)
                    continue
                if not file:
                    if engagement_type == "NOTE":
                        associations_to_delete.append({"id": attachment.id})
                    else:
                        deleted_attachments.append(file_id)
                    continue
                if file_type and file.type != file_type.value:
                    continue

                if deletion_type == FileDeletionType.GDPR_DELETE:
                    self.hubspot_client.files.files_api.archive_gdpr(file_id=file_id)
                elif deletion_type == FileDeletionType.DELETE:
                    self.hubspot_client.files.files_api.archive(file_id=file_id)
                else:
                    raise ValueError(f"Deletion type {deletion_type} is not supported")

                if engagement_type == "NOTE":
                    self.hubspot_client.crm.objects.basic_api.archive(
                        object_type=engagement_type, object_id=attachment.id
                    )

                    associations_to_delete.append({"id": attachment.id})
                else:
                    deleted_attachments.append(file_id)
            engagements_to_update_by_type[engagement_type].append(
                {
                    "id": attachment.id,
                    "properties": {
                        "hs_attachment_ids": ";".join(
                            [
                                attachment_id
                                for attachment_id in attachment_ids
                                if attachment_id not in deleted_attachments
                            ]
                        )
                    },
                }
            )
        if associations_to_delete:
            self.hubspot_client.crm.associations.v4.batch_api.archive(
                from_object_type=object_type,
                to_object_type=engagement_object_type,
                batch_input_public_association_multi_archive={
                    "inputs": [
                        {"from": {"id": object_id}, "to": associations_to_delete}
                    ]
                },
            )
        for engagement_type, inputs in engagements_to_update_by_type.items():
            self.update_objects_batch(object_type=engagement_type, inputs=inputs)

    def get_all_folders(self):
        folders = self.hubspot_client.files.folders_api.do_search(limit=100).to_dict()
        folder_list = folders["results"]
        while folders.get("paging") and folders.get("paging").get("next"):
            folder_list += self.hubspot_client.files.folders_api.do_search(
                limit=100, after=folders.get("paging").get("next").get("after")
            ).to_dict()["results"]

        return sorted(folder_list, key=lambda f: f"{f['path']}/{f['name']}")

    def get_all_files(self, **search_params) -> List[File]:
        if "limit" not in search_params:
            search_params["limit"] = 100
        files = self.hubspot_client.files.files_api.do_search(**search_params)
        file_list = files.results
        while files.paging and files.paging.next:
            file_list += self.hubspot_client.files.files_api.do_search(
                **search_params,
                after=files.paging.next.after,
            ).results

        return [File.model_validate(f.to_dict()) for f in file_list]

    def get_files_batch(self, file_ids: List[int]) -> List[File]:
        # format the list of file ids into repeated "id" query parameters
        query_params = urllib.parse.urlencode(
            [("id", file_id) for file_id in file_ids], doseq=True
        )

        resp = self.hubspot_client.files.files_api.api_client.request(
            method="GET",
            url=f"https://api.hubapi.com/files/v3/files/search?{query_params}",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return [File.model_validate(f) for f in json.loads(resp.data)["results"]]

    def create_page(self, page: dict):
        resp = self.hubspot_client.cms.domains.domains_api.api_client.request(
            method="POST",
            url="https://api.hubapi.com/cms/v3/pages/site-pages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            body=page,
        )
        return json.loads(resp.data)

    def create_list(self, list_json: dict) -> ListCreateResponse:
        return self.hubspot_client.crm.lists.lists_api.create(
            list_create_request=list_json
        )

    def add_members_to_list(self, list_id: int, object_ids: List[int]):
        self.hubspot_client.crm.lists.memberships_api.add(
            list_id=list_id, request_body=object_ids
        )

    def get_forms(self, after: str = None, limit: int = 100):
        return self.hubspot_client.marketing.forms.forms_api.get_page(
            limit=limit, after=after
        )

    def get_forms_as_workflow_options(
        self, q: str = None, after: str = None
    ) -> WorkflowOptionsResponse:
        forms = self.get_forms(after=after)
        options = [
            WorkflowFieldOption(label=form.name, description=form.name, value=form.id)
            for form in forms.results
            if not q or q.lower() in form.name.lower()
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=forms.paging.next.after if forms.paging else None,
            searchable=True,
        )

    def upsert_contact(self, properties: dict = None):
        if properties is None:
            return
        simple_public_object_input = {
            "properties": properties,
        }
        if "email" not in properties:
            return self.hubspot_client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )

        search_result = self.hubspot_client.crm.contacts.search_api.do_search(
            public_object_search_request=PublicObjectSearchRequest(
                filter_groups=[
                    {
                        "filters": [
                            {
                                "value": properties.get("email"),
                                "propertyName": "email",
                                "operator": "EQ",
                            }
                        ]
                    }
                ]
            )
        )
        if search_result.total == 0:
            self.hubspot_client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )
        else:
            self.hubspot_client.crm.contacts.basic_api.update(
                contact_id=search_result.results[0].id,
                simple_public_object_input=simple_public_object_input,
            )

    def get_marketing_events_as_workflow_options(
        self, q: str = None
    ) -> WorkflowOptionsResponse:
        events = [
            self.get_marketing_event(
                portal_id=event.external_account_id,
                external_event_id=event.external_event_id,
            )
            for event in self.get_marketing_events().results
        ]
        options = [
            WorkflowFieldOption(
                label=event.event_name, description=event.event_name, value=event.id
            )
            for event in events
            if not q or q.lower() in str(event.event_name).lower()
        ]
        return WorkflowOptionsResponse(options=options, after=None, searchable=True)

    def get_marketing_events_as_workflow_options_v2(
        self, q: str = None, after: str = None
    ) -> WorkflowOptionsResponse:
        response = self.get_marketing_events_v2(after=after)
        options = [
            WorkflowFieldOption(
                label=event.event_name,
                description=event.event_name,
                value=event.object_id,
            )
            for event in response.results
            if not q or q.lower() in str(event.event_name).lower()
        ]
        return WorkflowOptionsResponse(
            options=options,
            after=response.paging.next.after
            if response.paging and response.paging.next
            else None,
            searchable=True,
        )

    def get_marketing_events(self, q: str = "gohsme"):
        return self.hubspot_client.marketing.events.basic_api.do_search(q=q)

    def get_marketing_events_v2(
        self, limit: int = 100, after: str = None
    ) -> MarketingEventResultsWithPaging:
        query_params = {"limit": limit}
        if after:
            query_params["after"] = after
        resp = self.hubspot_client.marketing.events.basic_api.api_client.request(
            method="GET",
            url="https://api.hubapi.com/marketing/v3/marketing-events",
            query_params=query_params,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return MarketingEventResultsWithPaging.model_validate(json.loads(resp.data))

    def get_all_marketing_events(self) -> List[MarketingEvent]:
        events = self.get_marketing_events_v2()
        results = events.results
        while events.paging and events.paging.next:
            events = self.get_marketing_events_v2(after=events.paging.next.after)
            results += events.results
        return results

    def get_marketing_event(self, portal_id: int, external_event_id: str):
        return self.hubspot_client.marketing.events.basic_api.get_details(
            external_event_id=external_event_id, external_account_id=str(portal_id)
        )

    def create_marketing_event(self, marketing_event_create_request: MarketingEvent):
        return self.hubspot_client.marketing.events.basic_api.create(
            marketing_event_create_request_params=marketing_event_create_request.model_dump(
                by_alias=True, exclude_unset=True, exclude_none=True
            )
        )

    def get_marketing_event_participant_state(
        self, contact_id: str, limit: int = 100, after: str = None
    ) -> CollectionResponseWithTotalParticipationBreakdownForwardPaging:
        return self.hubspot_client.marketing.events.participant_state_api.get_participations_breakdown_by_contact_id(
            contact_identifier=contact_id, limit=limit, after=after
        )

    def update_marketing_event_subscriber_state_v2(
        self,
        object_id: int,
        contact_id: int,
        subscriber_state: SubscriberState,
        timestamp: int,
    ):
        # First verify the contact has never attended the event
        has_more = True
        after = None
        while has_more:
            participation_breakdown_response = (
                self.get_marketing_event_participant_state(
                    contact_id=str(contact_id), after=after
                )
            )
            has_more = (
                participation_breakdown_response.paging
                and participation_breakdown_response.paging.next
            )
            after = (
                participation_breakdown_response.paging.next.after if has_more else None
            )
            for result in participation_breakdown_response.results:
                breakdown: ParticipationBreakdown = result
                breakdown_properties: ParticipationProperties = breakdown.properties
                participation_associations: ParticipationAssociations = (
                    breakdown.associations
                )
                marketing_event_association: MarketingEventAssociation = (
                    participation_associations.marketing_event
                )
                if (
                    str(marketing_event_association.marketing_event_id)
                    == str(object_id)
                    and SubscriberState[breakdown_properties.attendance_state]
                    == subscriber_state
                ):
                    self.logger.log_info(
                        f"Contact {contact_id} has already {breakdown_properties.attendance_state.lower()} event {object_id}. Skip processing...",
                        labels={"contact_id": contact_id, "event_id": object_id},
                    )
                    return

        body = {"inputs": [{"vid": contact_id, "interactionDateTime": timestamp}]}
        try:
            resp = self.hubspot_client.marketing.events.basic_api.api_client.request(
                method="POST",
                url=f"https://api.hubapi.com/marketing/v3/marketing-events/{object_id}/attendance/{subscriber_state.value}/create",
                body=body,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            return json.loads(resp.data)
        except MarketingEventsException as e:
            if "Error: (429)" in str(e):
                raise
            self.logger.log_debug(
                f"Marketing Event {object_id} does not exist. Error: {str(e)}",
                labels={"event_id": object_id},
            )
            raise HubSpotWorkflowException(
                error_code=ErrorCode.INVALID_EVENT,
                message=f"Marketing Event {object_id} does not exist",
            )

    def update_marketing_event_subscriber_state(
        self,
        portal_id: int,
        external_event_id: str,
        contact_id: int,
        subscriber_state: SubscriberState,
        timestamp: int,
    ):
        try:
            return self.hubspot_client.marketing.events.attendance_subscriber_state_changes_api.record_by_contact_ids(
                external_event_id=external_event_id,
                subscriber_state=subscriber_state.value,
                batch_input_marketing_event_subscriber=BatchInputMarketingEventSubscriber(
                    inputs=[{"vid": contact_id, "interactionDateTime": timestamp}]
                ),
                external_account_id=str(portal_id),
            )
        except MarketingEventsException as e:
            if "Error: (429)" in str(e):
                raise
            self.logger.log_debug(
                f"Marketing Event {external_event_id} does not exist for portal {portal_id}. Error: {str(e)}",
                labels={
                    "event_id": external_event_id,
                    "portal_id": portal_id,
                    "contact_id": contact_id,
                },
            )
            raise HubSpotWorkflowException(
                error_code=ErrorCode.INVALID_EVENT,
                message=f"Marketing Event {external_event_id} does not exist for portal {portal_id}",
            )

    def update_marketing_event_subscriber_states_bulk(
        self,
        portal_id: int,
        external_event_id: str,
        subscriber_state: SubscriberState,
        inputs: List[dict],
    ):
        chunk_size = 100
        while inputs:
            chunk, inputs = inputs[:chunk_size], inputs[chunk_size:]
            self.hubspot_client.marketing.events.subscriber_state_changes_api.upsert_by_contact_id(
                external_event_id=external_event_id,
                subscriber_state=subscriber_state.value,
                batch_input_marketing_event_subscriber=BatchInputMarketingEventSubscriber(
                    inputs=chunk
                ),
                external_account_id=str(portal_id),
            )

    def complete_blocked_workflow_execution(
        self, callback_id: str, workflow_action_output: dict
    ):
        try:
            self.hubspot_client.automation.actions.callbacks_api.complete(
                callback_id=callback_id,
                callback_completion_request=workflow_action_output,
            )
        except AutomationException as e:
            if "CALLBACK_NOT_FOUND" not in str(e):
                raise e

    def complete_blocked_workflow_executions_for_callback_ids_list(
        self, callback_ids: List[str], output_data: Any = None
    ):
        chunk_size = 100
        while callback_ids:
            chunk, callback_ids = callback_ids[:chunk_size], callback_ids[chunk_size:]
            output_fields = {"hs_execution_state": ExecutionState.SUCCESS}
            if isinstance(output_data, dict):
                output_fields |= output_data
            inputs = [
                WorkflowActionCallback(
                    output_fields=ActionOutputFields(**output_fields),
                    callback_id=callback_id,
                )
                for callback_id in set(chunk)
            ]
            data = WorkflowActionCallbackBatch(inputs=inputs).model_dump(
                by_alias=True, exclude_none=True, exclude_unset=True
            )
            try:
                self.hubspot_client.automation.actions.callbacks_api.complete_batch(
                    batch_input_callback_completion_batch_request=data
                )
            except AutomationException as e:
                if "CALLBACK_NOT_FOUND" not in str(e):
                    raise e
                data = WorkflowActionCallbackBatch(
                    inputs=[i for i in inputs if i.callback_id not in str(e)]
                ).model_dump(by_alias=True, exclude_none=True, exclude_unset=True)
                self.hubspot_client.automation.actions.callbacks_api.complete_batch(
                    batch_input_callback_completion_batch_request=data
                )

    def complete_blocked_workflow_executions_bulk(self, callbacks: List[dict]):
        chunk_size = 100
        while callbacks:
            chunk, callbacks = callbacks[:chunk_size], callbacks[chunk_size:]
            try:
                self.hubspot_client.automation.actions.callbacks_api.complete_batch(
                    batch_input_callback_completion_batch_request={"inputs": chunk}
                )
            except AutomationException as e:
                if "CALLBACK_NOT_FOUND" not in str(e):
                    raise e
                chunk = [c for c in chunk if c["callbackId"] not in str(e)]
                self.hubspot_client.automation.actions.callbacks_api.complete_batch(
                    batch_input_callback_completion_batch_request={"inputs": chunk}
                )

    def get_products(self, after: str = None, limit: int = 100):
        return self.hubspot_client.crm.products.basic_api.get_page(
            limit=limit, after=after
        )

    def search_products(self, q: str = None, after: str = None, limit: int = 100):
        return self.hubspot_client.crm.products.search_api.do_search(
            public_object_search_request=PublicObjectSearchRequest(
                query=q,
                properties=["name", "hs_sku"],
                after=after,
                sorts=["name"],
                limit=limit,
            )
        )

    def get_products_as_workflow_options(
        self, q: str = None, after: str = None
    ) -> WorkflowOptionsResponse:
        products = self.search_products(q=q, after=after)

        def format_product_option(p):
            description = p.properties["name"]
            if p.properties.get("hs_sku"):
                description = f"SKU: {p.properties['hs_sku']}"
            return WorkflowFieldOption(
                label=p.properties["name"], description=description, value=p.id
            )

        options = [format_product_option(product) for product in products.results]
        response = WorkflowOptionsResponse(options=options)
        if products.paging:
            response.after = products.paging.next.after

        if len(products.results) > 0:
            response.searchable = True

        return response

    def create_timeline_event(self, timeline_event: TimelineEvent):
        return self.hubspot_client.crm.timeline.events_api.create(
            timeline_event=timeline_event.model_dump(
                by_alias=True, exclude_unset=True, exclude_none=True
            )
        )

    def create_timeline_events(self, inputs: List[TimelineEvent]):
        return self.hubspot_client.crm.timeline.events_api.create_batch(
            batch_input_timeline_event={
                "inputs": [
                    timeline_event.model_dump(
                        by_alias=True, exclude_unset=True, exclude_none=True
                    )
                    for timeline_event in inputs
                ]
            }
        )

    def get_subscription_types(self):
        return self.hubspot_client.communication_preferences.definition_api.get_page()

    def get_subscription_statuses(self, email: str):
        return (
            self.hubspot_client.communication_preferences.status_api.get_email_status(
                email_address=email
            )
        )

    def subscribe_contact(
        self,
        email: str,
        subscription_id: str,
        legal_basis: str,
        legal_basis_explanation: str,
    ):
        data = {
            "emailAddress": email,
            "subscriptionId": subscription_id,
            "legalBasis": legal_basis,
            "legalBasisExplanation": legal_basis_explanation,
        }
        return self.hubspot_client.communication_preferences.status_api.subscribe(
            public_update_subscription_status_request=data
        )

    def unsubscribe_contact(
        self,
        email: str,
        subscription_id: str,
        legal_basis: str,
        legal_basis_explanation: str,
    ):
        data = {
            "emailAddress": email,
            "subscriptionId": subscription_id,
            "legalBasis": legal_basis,
            "legalBasisExplanation": legal_basis_explanation,
        }
        return self.hubspot_client.communication_preferences.status_api.unsubscribe(
            public_update_subscription_status_request=data
        )

    @staticmethod
    def get_object_label_for_object_type_id(object_type_id: str) -> str:
        standard_object_types = {
            "0-2": "companies",
            "0-1": "contacts",
            "0-3": "deals",
            "0-5": "tickets",
            "0-421": "appointments",
            "0-48": "calls",
            "0-18": "communications",
            "0-410": "courses",
            "0-49": "emails",
            "0-19": "feedback_submissions",
            "0-52": "invoices",
            "0-136": "leads",
            "0-8": "line_items",
            "0-420": "listings",
            "0-54": "marketing_events",
            "0-47": "meetings",
            "0-46": "notes",
            "0-101": "payments",
            "0-7": "products",
            "0-14": "quotes",
            "0-162": "services",
            "0-69": "subscriptions",
            "0-27": "tasks",
            "0-115": "users",
        }
        return standard_object_types.get(object_type_id)
