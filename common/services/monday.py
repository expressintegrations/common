import json
import re
from datetime import datetime, timezone
from typing import List, Tuple, Union, Dict

from monday import MondayClient

from common.core.utils import is_json
from common.models.monday.api.account import Account
from common.models.monday.api.boards import SimpleBoard, BoardColumn
from common.models.monday.api.items import SimpleColumn, ColumnValue
from common.models.monday.api.me import Me
from common.models.monday.api.webhooks import WebhookResponse
from common.models.monday.api.workspace import Workspace
from common.models.monday.app_events import Subscription
from common.services.base import BaseService
from common.services.constants import UNSUPPORTED_MONDAY_COLUMN_TYPES, ALLOWABLE_SNOWFLAKE_PRIMARY_KEY_COLUMNS


class MondayService(BaseService):
    def __init__(
        self,
        access_token: str
    ) -> None:
        self.monday_client = MondayClient(token=access_token)
        super().__init__(
            log_name="services.monday",
            exclude_inputs=[
                "parse_item_with_column_values",
                "parse_value",
                "parse_item_column_values"
            ],
            exclude_outputs=[
                "parse_item_with_column_values",
                "parse_value",
                "parse_item_column_values"
            ]
        )

    def get_self(self) -> Me:
        return Me.model_validate(self.monday_client.me.get_details()['data']['me'])

    def apps_monetization_supported(self) -> bool:
        query = '''
        query {
            apps_monetization_status {
                is_supported
            }
        }
        '''

        return self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']['apps_monetization_status']['is_supported']

    def get_app_subscription(self) -> Subscription:
        query = '''
        query {
            app_subscription {
                plan_id,
                is_trial,
                renewal_date,
                days_left,
                billing_period
            }
        }
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        if len(data['app_subscription']) > 0:
            return Subscription.model_validate(data['app_subscription'][0])

    def get_account(self) -> Account:
        query = '''
        query {
            account {
                country_code,
                id,
                name,
                plan {
                    max_users,
                    period,
                    tier,
                    version
                },
                products {
                    id,
                    kind
                }
            }
        }
        '''
        return Account.model_validate(
            self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['account']
        )

    def get_active_board_ids(self):
        query = '''
            query {
              boards(state: active) {
                id
              }
            }
        '''
        return self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']['boards']

    def get_board(self, board_id):
        return self.monday_client.boards.fetch_boards_by_id(board_ids=board_id)['data']

    def get_boards(self, **params):
        clean_params = {
            k: v if v not in [None, ''] else 'null' for k, v in params.items()
        }
        return self.monday_client.boards.fetch_boards(**clean_params)['data']['boards']

    def get_boards_in_workspace(self, workspace_id: int) -> List[SimpleBoard]:
        page = 1
        limit = 100
        all_boards = []
        while True:
            query = f'''
                query {{
                    boards (page: {page}, limit: {limit}, workspace_ids: {workspace_id}) {{
                        id
                        name
                    }}
                }}
            '''
            boards = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['boards']
            all_boards += [SimpleBoard.model_validate(board) for board in boards]
            page += 1
            if len(boards) < 100:
                break
        return all_boards

    def get_board_columns(self, board_id) -> List[BoardColumn]:
        data = self.monday_client.boards.fetch_boards_by_id(board_ids=board_id)['data']
        columns = [
            BoardColumn.model_validate(c)
            for c in data['boards'][0]['columns']
            if c['type'] not in UNSUPPORTED_MONDAY_COLUMN_TYPES
        ]

        columns.insert(0, BoardColumn(id='id', title='Item ID', type='pulse-id'))
        return columns

    def get_workspaces(self) -> List[Workspace]:
        query = '''
            query {
                workspaces {
                    id
                    name
                    kind
                    description
                }
            }
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        workspaces = [Workspace.model_validate(item) for item in data['workspaces']]
        if 'Main workspace' not in [workspace.name for workspace in workspaces]:
            workspaces[0] = Workspace.model_validate(
                {
                    'name': 'Main workspace',
                    'kind': 'open'
                }
            )
        return workspaces

    def get_monday_column_options_for_snowflake(self, board_id):
        monday_board_columns = self.get_board_columns(board_id)

        def is_allowable_for_snowflake(column):
            return column['type'] in ALLOWABLE_SNOWFLAKE_PRIMARY_KEY_COLUMNS

        return list(
            map(
                lambda column: {'title': column['title'], 'value': column},
                filter(is_allowable_for_snowflake, monday_board_columns)
            )
        )

    def get_item_with_column_values(
        self,
        item_id,
        return_type='list'
    ) -> Union[List[ColumnValue] | Dict[str, ColumnValue]]:
        query = f'''
        query {{
            items (ids: [{item_id}]) {{
                group {{
                    id
                    title
                }}
                id
                name
                column_values {{
                  id
                  column {{
                    id
                    title
                  }}
                  text
                  type
                  value
                }}
            }}
        }}
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        item = data['items'][0]
        column_values = self.parse_item_column_values(item)

        if return_type == 'list':
            return column_values
        elif return_type == 'dict':
            return {v['id']: v for v in column_values}
        else:
            return column_values

    def get_items_with_column_values(
        self,
        board_id,
        limit: int = 100,
        cursor: str = None
    ) -> Tuple[List[List[ColumnValue]], str]:
        if not cursor:
            query = f'''
            query {{
                boards(ids: {board_id}) {{
                    name
                    items_page (limit: {limit}){{
                        cursor
                        items {{
                            group {{
                                id
                                title
                            }}
                            id
                            name
                            column_values {{
                              id
                              column {{
                                id
                                title
                              }}
                              text
                              type
                              value
                            }}
                        }}
                    }}
                }}
            }}
            '''
            data = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['boards'][0]['items_page']
            items = data['items']
            cursor = data['cursor']
        else:
            query = f'''
            query {{
                next_items_page (cursor: "{cursor}", limit: {limit}){{
                    cursor
                    items {{
                        group {{
                            id
                            title
                        }}
                        id
                        name
                        column_values {{
                          id
                          column {{
                            id
                            title
                          }}
                          text
                          type
                          value
                        }}
                    }}
                }}
            }}
            '''
            data = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['next_items_page']
            items = data['items']
            cursor = data['cursor']
        items_with_column_values = [self.parse_item_column_values(item) for item in items]
        return items_with_column_values, cursor

    def get_item_ids_by_column_value(self, board_id, column_id, column_value):
        data = self.monday_client.items.fetch_items_by_column_value(
            board_id=board_id,
            column_id=column_id,
            value=column_value,
            limit=100
        )['data']['items_page_by_column_values']
        item_ids = [item['id'] for item in data['items']]
        cursor = data['cursor']
        while cursor:
            query = f'''
                query {{
                    next_items_page(cursor: "{cursor}", limit: 100) {{
                        cursor
                        items {{
                            id
                        }}
                    }}
                }}
            '''
            data = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['next_items_page']
            item_ids += [item['id'] for item in data['items']]
            cursor = data['cursor']
        return item_ids

    def update_long_text_column_value(self, board_id, item_id, column_id, column_value):
        column_value_json = {
            'text': column_value
        }
        return self.monday_client.items.change_item_value(board_id, item_id, column_id, column_value_json)['data']

    def create_item(self, board_id: int, item_name: str, column_values: dict, group_id: str = None):
        if not group_id:
            query = f'''
                query {{
                    boards (ids: {board_id}){{
                        top_group {{
                            id
                        }}
                    }}
                }}
            '''
            group_id = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['boards'][0]['top_group']['id']
        self.monday_client.items.create_item(
            board_id=board_id,
            group_id=group_id,
            item_name=item_name,
            column_values=column_values,
            create_labels_if_missing=True
        )

    def update_item(self, board_id, item_id, column_values):
        self.monday_client.items.change_multiple_column_values(
            board_id=board_id,
            item_id=item_id,
            column_values=column_values,
            create_labels_if_missing=True
        )

    @staticmethod
    def parse_value(column):
        def add_text(item, text):
            item['text'] = re.sub(r'\\*\'', "\\'", text)
            return item
        if not column['value'] and (column['text'] == '' or column['text'] is None) and column['type'] not in ['votes']:
            return column
        if is_json(column['value']):
            column['value'] = json.loads(column['value'])
        if column['type'] in ['item_id', 'rating', 'auto_number']:
            column['value'] = int(column['text'])
        elif column['type'] == 'vote':
            if len(column['text']) > 0:
                column['value'] = int(column['text'])
            else:
                column['value'] = 0
        elif column['type'] == 'checkbox':
            column['value'] = str(column['value']['checked']) == 'true'
        elif column['type'] == 'date':
            if 'time' in column['value'] and column['value']['time']:
                date_time_str = f"{column['value']['date']} {column['value']['time']}"
                format_data = '%Y-%m-%d %H:%M:%S'
                dt = datetime.strptime(date_time_str, format_data)
                column['value'] = f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
            else:
                column['value'] = column['text']
        elif column['type'] in ['dependency', 'board_relation', 'subtasks']:
            if column['value'] is not None:
                column['value'] = [
                    add_text(item, column['text'].split(', ')[index]) if column['text'] else item
                    for index, item in enumerate(column['value']['linkedPulseIds'])
                ] if 'linkedPulseIds' in column['value'] else []
        elif column['type'] in ['dropdown', 'tags']:
            column['value'] = column['text'].split(', ') if column['text'] else column['text']
        elif column['type'] == 'people':
            if column['value'] is not None:
                # column['value'] = column['value']['personsAndTeams']
                column['value'] = [
                    add_text(item, column['text'].split(', ')[index])
                    for index, item in enumerate(column['value']['personsAndTeams'])
                ]
        elif column['type'] == 'file':
            column['value'] = column['value']['files']
        elif column['type'] == 'link':
            column['value'] = column['value']['url']
        elif column['type'] == 'numbers':
            if '.' in column['text']:
                column['value'] = float(column['text'])
            else:
                column['value'] = int(column['text']) if column['text'] and column['text'] != '' else 0
        elif column['type'] in ['creation_log', 'last_updated']:
            format_data = '%Y-%m-%d %H:%M:%S %Z'
            dt = datetime.strptime(column['text'], format_data)
            column['value'] = f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
        elif column['type'] == 'duration':
            # keep the column value as an object
            pass
        else:
            column['value'] = column['text']
        return column

    def parse_item_column_values(self, item) -> List[ColumnValue]:
        column_values = [
            ColumnValue.model_validate(self.parse_value(v))
            for v in item['column_values']
            if v['type'] not in UNSUPPORTED_MONDAY_COLUMN_TYPES
        ]
        # add the name and id columns, as those are not returned by default
        column_values.insert(
            0,
            ColumnValue(
                id='name',
                column=SimpleColumn(
                    id='name',
                    title='Item Name'
                ),
                type='name',
                value=item['name'],
                text=item['name']
            )
        )
        column_values.insert(
            0,
            ColumnValue(
                id='id',
                column=SimpleColumn(
                    id='id',
                    title='Item ID'
                ),
                type='item_id',
                value=int(item['id']),
                text=item['id']
            )
        )
        return column_values

    def get_users(self):
        data = self.monday_client.users.fetch_users()['data']
        return data['users']

    def get_teams(self):
        query = '''
        query {
            teams {
                id,
                picture_url,
                name,
                users {
                  id
                }
              }
        }
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        return data['teams']

    def get_board_activity(
        self,
        board_id: int,
        from_date: str,
        to_date: str,
        page: int,
        limit: int
    ) -> List[dict]:
        query = f'''
        query {{
            boards(ids: {board_id}) {{
                activity_logs(from: "{from_date}", to: "{to_date}", page: {page}, limit: {limit}) {{
                    id,
                    entity,
                    event,
                    user_id,
                    account_id
                    data,
                    created_at
                }}
            }}
        }}
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']

        def parse_data(activity_log) -> dict:
            activity_log['data'] = json.loads(activity_log['data'])
            return activity_log

        activity_logs = [parse_data(a) for a in data['boards'][0]['activity_logs']]
        return activity_logs

    def create_webhook(self, board_id, url, event, column_id=None) -> WebhookResponse:
        column_config = f', config: "{{\\"columnId\\": \\"{column_id}\\"}}"' if column_id else ''
        query = rf"""
        mutation {{
            create_webhook (board_id:{board_id}, url: "{url}", event: {event}{column_config}) {{
                id
                board_id
            }}
        }}
        """
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )
        if 'data' not in data:
            raise Exception(f"Failed to create webhook: {data}")

        return WebhookResponse.model_validate(data['data']['create_webhook'])

    def delete_webhook(self, webhook_id) -> WebhookResponse:
        query = f'''
        mutation {{
            delete_webhook (id:{webhook_id}) {{
                id
                board_id
            }}
        }}
        '''
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        return WebhookResponse.model_validate(data['delete_webhook'])
