import json
import re
from datetime import datetime, timezone

from monday import MondayClient

from common.core.utils import is_json
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
            exclude_outputs=[
                "parse_item_with_column_values",
                "parse_value",
                "parse_item_column_values"
            ]
        )

    def get_self(self):
        return self.monday_client.me.get_details()['data']['me']

    def apps_monetization_supported(self):
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

    def get_app_subscription(self):
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
        return data['app_subscription'][0] if len(data['app_subscription']) > 0 else None

    def get_account(self):
        query = '''
        query {
            account {
                slug,
                name
            }
        }
        '''
        return self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']['account']

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

    def get_board_ids(self, **params):
        params['page'] = 1
        clean_params = {
            k: v if v not in [None, ''] else 'null' for k, v in params.items()
        }
        board_ids = self.monday_client.boards.fetch_board_ids(**clean_params)['data']['boards']
        all_board_ids = list(board_ids)
        while len(board_ids) == 100:
            params['page'] += 1
            board_ids = self.monday_client.boards.fetch_board_ids(**clean_params)['data']['boards']
            all_board_ids += board_ids
        return all_board_ids

    def get_board_columns(self, board_id):
        data = self.monday_client.boards.fetch_boards_by_id(board_ids=board_id)['data']
        print(f"Get Boards Response: {data}")
        columns = [c for c in data['boards'][0]['columns'] if c['type'] not in UNSUPPORTED_MONDAY_COLUMN_TYPES]
        columns.insert(0, {'id': 'id', 'title': 'Item ID', 'type': 'pulse-id'})
        return columns

    def get_workspaces(self):
        data = self.monday_client.workspaces.get_workspaces()['data']
        return data['workspaces']

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

    def get_item_with_column_values(self, board_id, item_id, return_type='list'):
        query = '''
        query {
            boards(ids: %s) {
                name
                items_page {
                    cursor
                    items (ids: %s) {
                        group {
                            id
                            title
                        }
                        id
                        name
                        column_values {
                          id
                          column {
                            id
                            title
                          }
                          text
                          type
                          value
                        }
                    }
                }
            }
        }
        ''' % board_id, item_id
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        item = data['boards'][0]['items_page']['items'][0]
        column_values = self.parse_item_column_values(item)

        if return_type == 'list':
            return column_values
        elif return_type == 'dict':
            return {v['id']: v for v in column_values}
        else:
            return column_values

    def get_items_with_column_values(self, board_id, limit: int = 100, cursor: str = None):
        if not cursor:
            query = '''
            query {
                boards(ids: %s) {
                    name
                    items_page (limit: %s){
                        cursor
                        items {
                            group {
                                id
                                title
                            }
                            id
                            name
                            column_values {
                              id
                              column {
                                id
                                title
                              }
                              text
                              type
                              value
                            }
                        }
                    }
                }
            }
            ''' % (board_id, limit)
            data = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['boards'][0]['items_page']
            items = data['items']
            cursor = data['cursor']
        else:
            query = '''
            query {
                next_items_page (cursor: %s, limit: %s){
                    cursor
                    items {
                        group {
                            id
                            title
                        }
                        id
                        name
                        column_values {
                          id
                          title
                          text
                          type
                          value
                        }
                    }
                }
            }
            ''' % (cursor, limit)
            data = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )['data']['next_items_page']
            items = data['items']
            cursor = data['cursor']
        return [self.parse_item_column_values(item) for item in items], cursor

    def get_item_ids_by_column_value(self, board_id, column_id, column_value):
        data = self.monday_client.items.fetch_items_by_column_value(
            board_id=board_id,
            column_id=column_id,
            value=column_value,
            limit=100
        )['data']['items_page_by_column_values']
        item_ids = [item['id'] for item in data['items']]
        cursor = data['cursor']
        while len(data['items']) > 0:
            query = '''
            query {
                next_items_page(
                    cursor: "%s",
                    limit: 100
                ) {
                    cursor
                    items {
                        id
                    }
                }
            }''' % cursor
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

    def create_item(self, board_id, item_name, column_values):
        self.monday_client.items.create_item(
            board_id=board_id,
            group_id=None,
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
        if column['type'] in ['pulse-id', 'rating', 'autonumber']:
            column['value'] = int(column['text'])
        elif column['type'] == 'votes':
            if len(column['text']) > 0:
                column['value'] = int(column['text'])
            else:
                column['value'] = 0
        elif column['type'] == 'boolean':
            column['value'] = str(column['value']['checked']) == 'true'
        elif column['type'] == 'date':
            if 'time' in column['value'] and column['value']['time']:
                date_time_str = f"{column['value']['date']} {column['value']['time']}"
                format_data = '%Y-%m-%d %H:%M:%S'
                dt = datetime.strptime(date_time_str, format_data)
                column['value'] = f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
            else:
                column['value'] = column['text']
        elif column['type'] in ['dependency', 'board-relation', 'subtasks']:
            if column['value'] is not None:
                column['value'] = [
                    add_text(item, column['text'].split(', ')[index])
                    for index, item in enumerate(column['value']['linkedPulseIds'])
                ] if 'linkedPulseIds' in column['value'] else []
        elif column['type'] in ['dropdown', 'tag']:
            column['value'] = column['text'].split(', ') if column['text'] else column['text']
        elif column['type'] == 'multiple-person':
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
        elif column['type'] == 'numeric':
            if '.' in column['text']:
                column['value'] = float(column['text'])
            else:
                column['value'] = int(column['text']) if column['text'] and column['text'] != '' else 0
        elif column['type'] in ['pulse-log', 'pulse-updated']:
            format_data = '%Y-%m-%d %H:%M:%S %Z'
            dt = datetime.strptime(column['text'], format_data)
            column['value'] = f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
        elif column['type'] == 'duration':
            # keep the column value as an object
            pass
        else:
            column['value'] = column['text']
        return column

    def parse_item_column_values(self, item):
        column_values = [self.parse_value(v) for v in item['column_values'] if
                         v['type'] not in UNSUPPORTED_MONDAY_COLUMN_TYPES]
        # add the name and id columns, as those are not returned by default
        column_values.insert(
            0,
            {'id': 'name', 'title': 'Item Name', 'type': 'name', 'value': item['name'], 'text': item['name']}
        )
        column_values.insert(
            0,
            {'id': 'id', 'title': 'Item ID', 'type': 'pulse-id', 'value': int(item['id']), 'text': item['id']}
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

    def get_board_activity(self, board_id, from_date, to_date, page, limit):
        print(f"getting activity for {from_date} to {to_date}")
        query = '''
        query {
            boards(ids: %s) {
                activity_logs(from: "%s", to: "%s", page: %s, limit: %s) {
                    id,
                    entity,
                    event,
                    user_id,
                    account_id
                    data,
                    created_at
                }
            }
        }
        ''' % (board_id, from_date, to_date, page, limit)
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']

        def parse_data(activity_log):
            activity_log['data'] = json.loads(activity_log['data'])
            return activity_log

        activity_logs = [parse_data(a) for a in data['boards'][0]['activity_logs']]
        return activity_logs

    def create_webhook(self, board_id, url, event, column_id=None):
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
        )['data']
        return data['create_webhook']

    def delete_webhook(self, webhook_id):
        query = '''
        mutation {
            delete_webhook (id:%s) {
                id
                board_id
            }
        }
        ''' % webhook_id
        data = self.monday_client.custom.execute_custom_query(
            custom_query=query
        )['data']
        return data['delete_webhook']
