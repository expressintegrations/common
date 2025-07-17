import json
import re
import httpx
import aiohttp
import asyncio
from httpx_retries import RetryTransport, Retry
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict, Any

from monday import MondayClient
from monday.utils import gather_params

from common.core.utils import is_json
from common.logging.client import Logger
from common.models.monday.api.account import Account
from common.models.monday.api.boards import SimpleBoard, BoardColumn
from common.models.monday.api.items import ColumnDetails, ColumnValue
from common.models.monday.api.me import Me
from common.models.monday.api.webhooks import WebhookResponse
from common.models.monday.api.workspace import Workspace
from common.models.monday.app_events import Subscription
from common.services.base import BaseService
from common.services.constants import (
    UNSUPPORTED_MONDAY_COLUMN_TYPES,
    ALLOWABLE_SNOWFLAKE_PRIMARY_KEY_COLUMNS,
)
from monday_async import AsyncMondayClient
from monday_async.types.enum_values import State, BoardKind, BoardsOrderBy, ID
from aiohttp import ClientSession
import statistics
from simpleeval import simple_eval
import math
from common.models.monday.api.queries import Complexity


class ApiError(Exception):
    def __init__(self, url: str, status_code: int, message: str) -> None:
        self.url = url
        self.status_code = status_code
        self.message = message
        super().__init__(
            f"Monday API Error: request to {url} failed with status {status_code}: {message}"
        )


class MondayService(BaseService):
    def __init__(
        self,
        access_token: str,
        logger: Logger | None = None,
    ) -> None:
        self.access_token = access_token
        self.monday_client = MondayClient(token=access_token)
        self.retry_policy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 503, 504],
        )
        self.httpx_client = httpx.AsyncClient(
            transport=RetryTransport(
                retry=self.retry_policy,
            )
        )
        super().__init__(
            log_name="services.monday",
            logger=logger,
        )

    async def _make_request(
        self, url: str, method: str = "GET", **kwargs: Any
    ) -> dict[str, Any]:
        self.logger.log_debug(f"Making {method} request to {url} with params: {kwargs}")
        try:
            response: httpx.Response = await self.httpx_client.request(
                method=method,
                url=url,
                **kwargs,
            )
            response.raise_for_status()
            if response.headers.get("Content-Type") == "application/json":
                return response.json()

            return {
                "status_code": response.status_code,
                "content": response.text,
            }
        except httpx.HTTPStatusError as e:
            self.logger.log_error(
                f"HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise ApiError(
                url=url,
                status_code=e.response.status_code,
                message=e.response.text,
            ) from e
        except httpx.RequestError as e:
            self.logger.log_error(f"Request error: {e}")
            raise ApiError(
                url=url,
                status_code=500,
                message="Internal Server Error",
            ) from e

    async def close(self) -> None:
        await self.httpx_client.aclose()

    async def __aenter__(self) -> "MondayService":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def post(
        self, url: str, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        return await self._make_request(url, method="POST", json=json, **kwargs)

    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return await self._make_request(url, method="GET", **kwargs)

    async def invoke_monday_integration_webhook(
        self,
        url: str,
        json: dict[str, Any],
        signing_secret: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": signing_secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return await self.post(url, json=json, headers=headers)

    def get_self(self) -> Me:
        return Me.model_validate(self.monday_client.me.get_details()["data"]["me"])

    def apps_monetization_supported(self) -> bool:
        query = """
        query {
            apps_monetization_status {
                is_supported
            }
        }
        """

        return self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]["apps_monetization_status"]["is_supported"]

    def get_app_subscription(self) -> Subscription | None:
        query = """
        query {
            app_subscription {
                plan_id,
                is_trial,
                renewal_date,
                days_left,
                billing_period
            }
        }
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]
        if len(data["app_subscription"]) > 0:
            return Subscription.model_validate(data["app_subscription"][0])

    def get_account(self) -> Account:
        query = """
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
        """
        return Account.model_validate(
            self.monday_client.custom.execute_custom_query(custom_query=query)["data"][
                "account"
            ]
        )

    def get_active_board_ids(self):
        query = """
            query {
              boards(state: active) {
                id
                name
              }
            }
        """
        return self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]["boards"]

    def get_board(self, board_id):
        return self.monday_client.boards.fetch_boards_by_id(board_ids=board_id)["data"]

    def get_boards(self, **params):
        clean_params = {
            k: v if v not in [None, ""] else "null" for k, v in params.items()
        }
        return self.monday_client.boards.fetch_boards(**clean_params)["data"]["boards"]  # type: ignore

    def get_boards_in_workspace(self, workspace_id: int) -> List[SimpleBoard]:
        page = 1
        limit = 100
        all_boards = []
        while True:
            query = f"""
                query {{
                    boards (page: {page}, limit: {limit}, workspace_ids: {workspace_id}) {{
                        id
                        name
                    }}
                }}
            """
            boards = self.monday_client.custom.execute_custom_query(custom_query=query)[
                "data"
            ]["boards"]
            all_boards += [SimpleBoard.model_validate(board) for board in boards]
            page += 1
            if len(boards) < 100:
                break
        return all_boards

    def get_board_columns(self, board_id) -> List[BoardColumn]:
        data = self.monday_client.boards.fetch_boards_by_id(board_ids=board_id)["data"]
        columns = [
            BoardColumn.model_validate(c)
            for c in data["boards"][0]["columns"]
            if c["type"] not in UNSUPPORTED_MONDAY_COLUMN_TYPES
        ]

        columns.insert(0, BoardColumn(id="id", title="Item ID", type="pulse-id"))
        return columns

    def get_workspaces(self) -> List[Workspace]:
        query = """
            query {
                workspaces {
                    id
                    name
                    kind
                    description
                }
            }
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]
        workspaces = [Workspace.model_validate(item) for item in data["workspaces"]]
        if "Main workspace" not in [workspace.name for workspace in workspaces]:
            workspaces[0] = Workspace.model_validate(
                {"name": "Main workspace", "kind": "open"}
            )
        return workspaces

    def get_monday_column_options_for_snowflake(self, board_id):
        monday_board_columns = self.get_board_columns(board_id)

        def is_allowable_for_snowflake(column: BoardColumn):
            return column.type in ALLOWABLE_SNOWFLAKE_PRIMARY_KEY_COLUMNS

        return list(
            map(
                lambda column: {"title": column.title, "value": column},
                filter(is_allowable_for_snowflake, monday_board_columns),
            )
        )

    def get_item_with_column_values(
        self, item_id, return_type="list"
    ) -> List[ColumnValue] | Dict[str, ColumnValue]:
        query = f"""
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
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]
        item = data["items"][0]
        column_values = self.parse_item_column_values(item)

        if return_type == "list":
            return column_values
        elif return_type == "dict":
            return {v.id: v for v in column_values}
        else:
            return column_values

    def get_items_with_column_values(
        self,
        board_id,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Tuple[List[List[ColumnValue]], str | None]:
        if not cursor:
            query = f"""
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
            """
            data = self.monday_client.custom.execute_custom_query(custom_query=query)[
                "data"
            ]["boards"][0]["items_page"]
            items = data["items"]
            cursor = data["cursor"]
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
            data = self.monday_client.custom.execute_custom_query(custom_query=query)[
                "data"
            ]["next_items_page"]
            items = data["items"]
            cursor = data["cursor"]
        items_with_column_values = [
            self.parse_item_column_values(item) for item in items
        ]
        return items_with_column_values, cursor

    def get_item_ids_by_column_value(self, board_id, column_id, column_value):
        query = _get_item_query_without_updates(
            board_id=board_id,
            column_id=column_id,
            value=column_value,
            limit=100,
        )
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]["items_page_by_column_values"]
        item_ids = [item["id"] for item in data["items"]]
        cursor = data["cursor"]
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
            data = self.monday_client.custom.execute_custom_query(custom_query=query)[
                "data"
            ]["next_items_page"]
            item_ids += [item["id"] for item in data["items"]]
            cursor = data["cursor"]
        return item_ids

    def update_long_text_column_value(self, board_id, item_id, column_id, column_value):
        column_value_json = {"text": column_value}
        return self.monday_client.items.change_item_value(
            board_id, item_id, column_id, column_value_json
        )["data"]

    def create_item(
        self,
        board_id: int,
        item_name: str,
        column_values: dict,
        group_id: str | None = None,
    ):
        if not group_id:
            query = f"""
                query {{
                    boards (ids: {board_id}){{
                        top_group {{
                            id
                        }}
                    }}
                }}
            """
            group_id = self.monday_client.custom.execute_custom_query(
                custom_query=query
            )["data"]["boards"][0]["top_group"]["id"]
        self.monday_client.items.create_item(
            board_id=board_id,
            group_id=group_id,
            item_name=item_name,
            column_values=column_values,
            create_labels_if_missing=True,
        )

    def update_item(self, board_id, item_id, column_values):
        self.monday_client.items.change_multiple_column_values(
            board_id=board_id,
            item_id=item_id,
            column_values=column_values,
            create_labels_if_missing=True,
        )

    def parse_value(self, column: dict, column_values_by_column_id: dict):
        def add_text(col, text):
            col["text"] = re.sub(r"\\*\'", "\\'", text)
            return col

        if (
            not column["value"]
            and (column["text"] == "" or column["text"] is None)
            and column["type"] not in ["votes", "formula", "mirror"]
        ):
            return column
        if is_json(column["value"]):
            column["value"] = json.loads(column["value"])
        if column["type"] in ["rating", "auto_number"]:
            column["value"] = int(column["text"])
        elif column["type"] == "vote":
            if len(column["text"]) > 0:
                column["value"] = int(column["text"])
            else:
                column["value"] = 0
        elif column["type"] == "checkbox":
            if "checked" in column:
                column["value"] = column["checked"]
            else:
                column["value"] = str(column["value"]["checked"]) == "true"
        elif column["type"] == "date":
            if "time" in column["value"] and column["value"]["time"]:
                date_time_str = f"{column['value']['date']} {column['value']['time']}"
                format_data = "%Y-%m-%d %H:%M:%S"
                dt = datetime.strptime(date_time_str, format_data)
                column["value"] = (
                    f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
                )
            else:
                column["value"] = column["text"]
        elif column["type"] in ["dependency", "board_relation", "subtasks"]:
            if column["value"] is not None:
                column["value"] = (
                    [
                        add_text(item, column["text"].split(", ")[index])
                        if column["text"]
                        else item
                        for index, item in enumerate(column["value"]["linkedPulseIds"])
                    ]
                    if "linkedPulseIds" in column["value"]
                    else []
                )
        elif column["type"] in ["dropdown", "tags"]:
            column["value"] = (
                column["text"].split(", ") if column["text"] else column["text"]
            )
        elif column["type"] == "people":
            if column["value"] is not None:
                # column['value'] = column['value']['personsAndTeams']
                column["value"] = [
                    add_text(item, column["text"].split(", ")[index])
                    for index, item in enumerate(column["value"]["personsAndTeams"])
                ]
        elif column["type"] == "file":
            column["value"] = column["value"]["files"]
        elif column["type"] == "link":
            column["value"] = column["value"]["url"]
        elif column["type"] == "numbers":
            if "." in column["text"]:
                column["value"] = float(column["text"])
            else:
                column["value"] = (
                    int(column["text"])
                    if column["text"] and column["text"] != ""
                    else 0
                )
        elif column["type"] in ["creation_log", "last_updated"]:
            format_data = "%Y-%m-%d %H:%M:%S %Z"
            dt = datetime.strptime(column["text"], format_data)
            column["value"] = f"{dt.replace(tzinfo=timezone.utc):%Y-%m-%d %H:%M:%S %z}"
        elif column["type"] in ["duration", "integration"]:
            # keep the column value as an object
            pass
        elif column["type"] == "formula" and "display_value" in column:
            column["value"] = column["display_value"]
            if column["display_value"] != "null":
                return column
            # This means the formula probably failed due to a mirror column being used in the formula
            # We need to parse the settings string to understand how to fix it
            settings_str = column["column"].get("settings_str")
            if not settings_str:
                return column

            settings_str = json.loads(settings_str)
            # Settings string example: "{\"formula\":\"{numeric_mksy5jn0}-{lookup_mksyak9f}\"}"
            formula = settings_str.get("formula")
            if not formula:
                return column

            # Find all column names in the formula
            column_names = re.findall(r"\{(\w+)\}", formula)
            if not column_names:
                return column

            # Replace the column names with the values
            for column_name in column_names:
                formula_column = column_values_by_column_id.get(column_name)
                if not formula_column:
                    # If any column name is not found, the formula is invalid
                    return column

                formula_column_value = self.parse_value(
                    formula_column, column_values_by_column_id
                )
                replacement_value = formula_column_value["value"]
                if formula_column_value["type"] == "mirror":
                    replacement_value = formula_column_value["value"]["display_value"]
                elif formula_column_value["type"] == "text":
                    replacement_value = f'\\"{replacement_value}\\"'

                if replacement_value in [None, "", "null"]:
                    replacement_value = 0
                formula = formula.replace(
                    f"{{{column_name}}}#Labels", str(replacement_value)
                ).replace(f"{{{column_name}}}", str(replacement_value))

            # The IF function needs to make sure the condition uses double equals instead of single equals
            formula = (
                formula.replace("=", "==")
                .replace("<==", "<=")
                .replace(">==", ">=")
                .replace("!==", "!=")
            )

            # We also see patterns like IF(['Net'] == 'Net', 1, 0), which should evaluate to 1 even though the comparison is between a list and a string
            def remove_single_element_brackets(expression):
                # Pattern to match single-element lists like ['content'] or ["content"]
                pattern = r"\[(['\"])([^,\]]*?)\1\]"

                def replace_match(match):
                    quote = match.group(1)  # ' or "
                    content = match.group(2)  # the content inside
                    return (
                        f"{quote}{content}{quote}"  # Return just 'content' or "content"
                    )

                return re.sub(pattern, replace_match, expression)

            formula = remove_single_element_brackets(formula)
            try:
                format_map = {
                    "$#,##0.00": "${:,.2f}",
                    "#,##0.00": "{:,.2f}",
                    "#,##0": "{:,}",
                    "0.00": "{:.2f}",
                    "0": "{}",
                }

                def search(find_text, within_text, start_num=1):
                    pos = within_text.lower().find(find_text.lower(), start_num - 1)
                    return pos + 1 if pos != -1 else None

                def switch_func(value, *args):
                    # Check if we have a default (odd number of args)
                    has_default = len(args) % 2 == 1
                    pairs = args[:-1] if has_default else args
                    default = args[-1] if has_default else None

                    # Look for matching value in pairs
                    for i in range(0, len(pairs), 2):
                        if pairs[i] == value:
                            return pairs[i + 1]

                    return default

                def workdays_func(to_date, from_date):
                    # Convert strings to datetime if needed
                    if isinstance(to_date, str):
                        to_date = datetime.strptime(to_date, "%Y-%m-%d")
                    if isinstance(from_date, str):
                        from_date = datetime.strptime(from_date, "%Y-%m-%d")

                    # Ensure start is before end
                    start = min(to_date, from_date)
                    end = max(to_date, from_date)

                    # Count working days (Monday=0 to Friday=4)
                    working_days = 0
                    current_date = start

                    while current_date <= end:
                        if current_date.weekday() < 5:  # Monday to Friday
                            working_days += 1
                        current_date += timedelta(days=1)

                    return working_days

                def workday_func(start_date, num_days):
                    # Convert string to datetime if needed
                    if isinstance(start_date, str):
                        start_date = datetime.strptime(start_date, "%Y-%m-%d")

                    current_date = start_date
                    days_added = 0
                    direction = 1 if num_days > 0 else -1
                    target_days = abs(num_days)

                    while days_added < target_days:
                        current_date += timedelta(days=direction)
                        # Count only weekdays (Monday=0 to Friday=4)
                        if current_date.weekday() < 5:
                            days_added += 1

                    return current_date

                def datevalue_func(date_text):
                    # Convert to string if not already
                    date_str = str(date_text)

                    # Try different date formats
                    formats = [
                        "%Y-%m-%d",
                        "%m/%d/%Y",
                        "%d/%m/%Y",
                        "%Y/%m/%d",
                        "%m-%d-%Y",
                        "%d-%m-%Y",
                    ]

                    for fmt in formats:
                        try:
                            date_obj = datetime.strptime(date_str, fmt)
                            # Excel's epoch is January 1, 1900 (with adjustment for leap year bug)
                            return (date_obj - datetime(1900, 1, 1)).days + 2
                        except ValueError:
                            continue

                    raise ValueError(f"Unable to parse date: {date_text}")

                def if_func(condition, true_value, false_value):
                    if condition:
                        return true_value
                    else:
                        return false_value

                column["value"] = simple_eval(
                    formula,
                    functions={
                        "AVERAGE": lambda *args: sum(args) / len(args),
                        "COUNT": lambda *args: len(args),
                        "SUM": lambda *args: sum(args),
                        "MOD": lambda x, y: x % y,
                        "ROUND": lambda x, y: round(x, y),
                        "ROUNDUP": lambda x, d: math.ceil(x * (10**d)) / (10**d),
                        "ROUNDDOWN": lambda x, d: math.floor(x * (10**d)) / (10**d),
                        "LOG": lambda x, b: math.log(x, b),
                        "MIN": lambda *args: min(args),
                        "MAX": lambda *args: max(args),
                        "MINUS": lambda x, y: x - y,
                        "MULTIPLY": lambda x, y: x * y,
                        "DIVIDE": lambda x, y: x / y,
                        "POWER": lambda x, y: x**y,
                        "SQRT": lambda x: x**0.5,
                        "IF": if_func,
                        "SWITCH": switch_func,
                        "TEXT": lambda x, y: format_map[y].format(
                            float(x) if "#" in y else int(float(x))
                        ),
                        "CONCATENATE": lambda *args: "".join(args),
                        "REPLACE": lambda text, start, num_chars, new_text: text[
                            : start - 1
                        ]
                        + new_text
                        + text[start - 1 + num_chars :],
                        "SUBSTITUTE": lambda text, old, new: text.replace(old, new),
                        "SEARCH": search,
                        "LEFT": lambda text, num_chars: text[:num_chars],
                        "RIGHT": lambda text, num_chars: text[-num_chars:],
                        "LEN": lambda text: len(text),
                        "REPT": lambda text, num_times: text * num_times,
                        "TRIM": lambda text: text.strip(),
                        "UPPER": lambda text: text.upper(),
                        "LOWER": lambda text: text.lower(),
                        "PI": lambda: math.pi,
                        "TRUE": lambda: True,
                        "FALSE": lambda: False,
                        "DATE": lambda y, m, d: datetime(y, m, d).strftime("%Y-%m-%d"),
                        "DAYS": lambda start_date, end_date: (
                            end_date - start_date
                        ).days,
                        "WORKDAYS": workdays_func,
                        "TODAY": lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "FORMAT_DATE": lambda date, format_str: datetime.strptime(
                            date, format_str
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "YEAR": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).year,
                        "MONTH": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).month,
                        "WEEKNUM": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).isocalendar()[1],
                        "ISOWEEKNUM": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).isocalendar()[1],
                        "DAY": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).day,
                        "HOUR": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).hour,
                        "MINUTE": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).minute,
                        "SECOND": lambda date: datetime.strptime(
                            date, "%Y-%m-%d %H:%M:%S"
                        ).second,
                        "ADD_DAYS": lambda date, days: (
                            datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                            + timedelta(days=days)
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "SUBTRACT_DAYS": lambda date, days: (
                            datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                            - timedelta(days=days)
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "ADD_MINUTES": lambda date, minutes: (
                            datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                            + timedelta(minutes=minutes)
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "SUBTRACT_MINUTES": lambda date, minutes: (
                            datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                            - timedelta(minutes=minutes)
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "HOURS_DIFF": lambda date1, date2: (
                            datetime.strptime(date1, "%Y-%m-%d %H:%M:%S")
                            - datetime.strptime(date2, "%Y-%m-%d %H:%M:%S")
                        ).total_seconds()
                        / 3600,
                        "WORKDAY": workday_func,
                        "DATEVALUE": datevalue_func,
                    },
                )
            except Exception as e:
                if "float division by zero" in str(e):
                    column["value"] = 0
                else:
                    self.logger.error(
                        f"Error evaluating formula ({formula}): {e}",
                        labels={
                            "formula": formula,
                            "column_name": column["column"]["title"],
                            "column_value": formula_column_value,
                            "replacement_value": replacement_value,
                            "settings_str": column["column"].get("settings_str"),
                        },
                    )

        elif column["type"] == "mirror":
            settings_str = column["column"].get("settings_str") or "{}"
            settings = json.loads(settings_str)
            # Settings string example: "{\"relation_column\":{\"subitems\":true},\"displayed_column\":{},\"displayed_linked_columns\":{\"4154746971\":[\"numeric_mkpy9ap3\"]},\"function\":\"sum\"}"
            # If the function is a math function, we need to apply it to the values of the mirrored items
            function = settings.get("function")
            evaluated_value = column.get("display_value")
            if function == "sum":
                values = column["display_value"].split(", ")
                evaluated_value = sum(float(v.strip()) for v in values if v.strip())
            elif function == "average":
                values = column["display_value"].split(", ")
                evaluated_value = sum(
                    float(v.strip()) for v in values if v.strip()
                ) / len(values)
            elif function == "min":
                values = column["display_value"].split(", ")
                evaluated_value = min(float(v.strip()) for v in values if v.strip())
            elif function == "max":
                values = column["display_value"].split(", ")
                evaluated_value = max(float(v.strip()) for v in values if v.strip())
            elif function == "count":
                values = column["display_value"].split(", ")
                evaluated_value = len(values)
            elif function == "median":
                values = column["display_value"].split(", ")
                evaluated_value = statistics.median(
                    float(v.strip()) for v in values if v.strip()
                )
            column["value"] = {
                "display_value": evaluated_value,
                "mirrored_items": column.get("mirrored_items", []),
            }
        else:
            column["value"] = column["text"]
        return column

    def parse_item_column_values(self, item) -> List[ColumnValue]:
        column_values_by_column_id = {}
        for v in item["column_values"]:
            column_values_by_column_id[v["id"]] = v
        column_values = [
            ColumnValue.model_validate(self.parse_value(v, column_values_by_column_id))
            for v in item["column_values"]
            if v["type"] not in UNSUPPORTED_MONDAY_COLUMN_TYPES
        ]
        # add the name and id columns, as those are not returned by default
        column_values.insert(
            0,
            ColumnValue(
                id="name",
                column=ColumnDetails(title="Item Name"),
                type="name",
                value=item["name"],
                text=item["name"],
            ),
        )
        column_values.insert(
            0,
            ColumnValue(
                id="id",
                column=ColumnDetails(title="Item ID"),
                type="item_id",
                value=int(item["id"]),
                text=item["id"],
            ),
        )
        return column_values

    def get_users(self):
        data = self.monday_client.users.fetch_users()["data"]
        return data["users"]

    def get_teams(self):
        query = """
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
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]
        return data["teams"]

    def get_board_activity(
        self, board_id: int, from_date: str, to_date: str, page: int, limit: int
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
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]

        def parse_data(activity_log) -> dict:
            activity_log["data"] = json.loads(activity_log["data"])
            return activity_log

        activity_logs = [parse_data(a) for a in data["boards"][0]["activity_logs"]]
        return activity_logs

    def create_webhook(self, board_id, url, event, column_id=None) -> WebhookResponse:
        column_config = (
            f', config: "{{\\"columnId\\": \\"{column_id}\\"}}"' if column_id else ""
        )
        query = rf"""
        mutation {{
            create_webhook (board_id:{board_id}, url: "{url}", event: {event}{column_config}) {{
                id
                board_id
            }}
        }}
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)
        if "data" not in data:
            raise Exception(f"Failed to create webhook: {data}")

        return WebhookResponse.model_validate(data["data"]["create_webhook"])

    def delete_webhook(self, webhook_id) -> WebhookResponse:
        query = f"""
        mutation {{
            delete_webhook (id:{webhook_id}) {{
                id
                board_id
            }}
        }}
        """
        data = self.monday_client.custom.execute_custom_query(custom_query=query)[
            "data"
        ]
        return WebhookResponse.model_validate(data["delete_webhook"])

    ###### ASYNC METHODS ######

    async def _execute_with_session(self, operation, max_retries=3):
        """Execute an operation with session management and retry logic"""
        timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_read=10)
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )

        last_exception = None

        for attempt in range(max_retries + 1):
            session = None
            try:
                session = aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    raise_for_status=True,
                )
                async_monday_client = AsyncMondayClient(
                    token=self.access_token,
                    session=session,
                )
                result = await operation(async_monday_client)
                await session.close()
                return result

            except (
                aiohttp.ClientError,
                aiohttp.ServerDisconnectedError,
                asyncio.TimeoutError,
                ConnectionResetError,
            ) as e:
                last_exception = e

                if attempt == max_retries:
                    if session:
                        await session.close()
                    raise e

                if session:
                    await session.close()

                delay = min(2**attempt, 10)
                await asyncio.sleep(delay)

        raise last_exception

    async def get_self_async(self) -> Me:
        async def operation(client):
            data = await client.users.get_me()
            return Me.model_validate(data["data"]["me"])

        return await self._execute_with_session(operation)

    async def create_webhook_async(
        self, board_id, url, event, column_id=None
    ) -> WebhookResponse:
        async def operation(client):
            response = await client.webhooks.create_webhook(
                board_id=board_id,
                url=url,
                event=event,
                config={"columnId": column_id} if column_id else None,
            )
            if "data" not in response:
                raise Exception(f"Failed to create webhook: {response}")

            return WebhookResponse.model_validate(response["data"]["create_webhook"])

        return await self._execute_with_session(operation)

    async def get_item_with_column_values_async(
        self, item_id, return_type="list"
    ) -> List[ColumnValue] | Dict[str, ColumnValue]:
        async def operation(client):
            response = await client.items.get_items_by_id(
                ids=[item_id],
            )
            item = response["data"]["items"][0]
            column_values = self.parse_item_column_values(item)
            if return_type == "list":
                return column_values
            elif return_type == "dict":
                return {v.id: v for v in column_values}
            else:
                return column_values

        return await self._execute_with_session(operation)

    async def get_boards_async(
        self,
        ids: ID | List[ID] | None = None,
        board_kind: BoardKind | None = None,
        state: State | None = None,
        workspace_ids: ID | List[ID] | None = None,
        order_by: BoardsOrderBy | None = None,
        limit: int | None = None,
        page: int | None = None,
    ):
        async def operation(client):
            return await client.boards.get_boards(
                ids=ids if ids is not None else [],
                board_kind=board_kind,
                state=state if state is not None else State.ACTIVE,
                workspace_ids=workspace_ids if workspace_ids is not None else [],
                order_by=order_by,
                limit=limit if limit is not None else 25,
                page=page if page is not None else 1,
            )

        return await self._execute_with_session(operation)

    async def get_board_columns_async(self, board_id) -> List[BoardColumn]:
        response = await self.get_boards_async(ids=board_id)
        columns = [
            BoardColumn.model_validate(c)
            for c in response["data"]["boards"][0]["columns"]
            if c["type"] not in UNSUPPORTED_MONDAY_COLUMN_TYPES
        ]

        columns.insert(0, BoardColumn(id="id", title="Item ID", type="pulse-id"))
        return columns

    async def get_items_with_column_values_async(
        self,
        board_id,
        limit: int = 100,
        cursor: str | None = None,
    ) -> Tuple[List[List[ColumnValue]], str | None, Complexity]:
        async def operation(client):
            response = await client.items.get_items_by_board(
                board_ids=board_id,
                limit=limit,
                cursor=cursor,
                with_complexity=True,
            )
            items_page = response["data"]["boards"][0]["items_page"]
            items = items_page["items"]
            next_cursor = items_page["cursor"]
            items_with_column_values = [
                self.parse_item_column_values(item) for item in items
            ]
            return (
                items_with_column_values,
                next_cursor,
                Complexity.model_validate(response["data"]["complexity"]),
            )

        return await self._execute_with_session(operation)


def _get_item_query_without_updates(
    board_id, column_id, value, limit=None, cursor=None
):
    columns = (
        [{"column_id": str(column_id), "column_values": [str(value)]}]
        if not cursor
        else None
    )

    raw_params = locals().items()
    items_page_params = gather_params(
        raw_params, excluded_params=["column_id", "value"]
    )

    query = (
        """query
        {
            items_page_by_column_values (%s) {
                cursor
                items {
                    id
                    name
                    group {
                        id
                        title
                    }
                    column_values {
                        id
                        text
                        value
                    }                
                }
            }
        }"""
        % items_page_params
    )

    return query
