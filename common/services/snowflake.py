import base64
import json
from typing import List

import snowflake.connector
from snowflake.connector.errors import ProgrammingError

from common.models.firestore.connections import Authorization
from common.services.base import BaseService

URL_CLOUD_PLATFORMS = [
    "us-east-1",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
    "ap-southeast-2",
]


class SnowflakeIntegrationException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class SnowflakeService(BaseService):
    def __init__(
        self,
        account_identifier: str,
        region: str,
        cloud_platform: str,
        username: str,
        role: str,
        warehouse: str,
        redirect_uri: str = None,
        access_token: str = None,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        password: str = None,
        paramstyle: str = None,
    ) -> None:
        super().__init__(log_name="services.snowflake", private_output=False)
        if paramstyle:
            snowflake.connector.paramstyle = paramstyle
        self.redirect_uri = redirect_uri
        self.account_identifier = account_identifier
        self.account_url = account_identifier
        self.username = username
        self.role = role
        self.warehouse = warehouse
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.password = password
        if region:
            self.account_url = f"{self.account_url}.{region}"
            if region.lower() not in URL_CLOUD_PLATFORMS:
                self.account_url = f"{self.account_url}.{cloud_platform.lower()}"
        self.connected = False
        self.ctx = None

    def connect(self):
        try:
            if self.access_token:
                self.ctx = snowflake.connector.connect(
                    user=self.username,
                    account=self.account_url,
                    authenticator="oauth",
                    token=self.access_token,
                    warehouse=self.warehouse,
                    role=self.role,
                )
            elif self.password:
                self.ctx = snowflake.connector.connect(
                    user=self.username,
                    password=self.password,
                    account=self.account_url,
                    warehouse=self.warehouse,
                    role=self.role,
                )
            else:
                raise SnowflakeIntegrationException("No authentication method provided")
        except Exception as e:
            raise SnowflakeIntegrationException(str(e))
        self.connected = True

    def refresh_snowflake_token(self) -> Authorization:
        url = f"https://{self.account_url}.snowflakecomputing.com/oauth/token-request"
        credentials = f"{self.client_id}:{self.client_secret}"
        headers = {
            "Authorization": f"Basic {base64.b64encode(credentials.encode('UTF-8')).decode('UTF-8')}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "redirect_uri": self.redirect_uri,
            "refresh_token": self.refresh_token,
        }
        import requests

        r = requests.post(url, data=data, headers=headers)
        if r.status_code >= 400:
            raise Exception(f"Attempted reauthorization: {r.status_code} {r.text}")
        r = r.json()
        if "error" in r:
            raise SnowflakeIntegrationException(
                f"Error: {r['error']}, Message: {r['message']}"
            )
        authorization = Authorization.model_validate(r)
        self.access_token = authorization.access_token
        return authorization

    def execute(self, query, keep_alive: bool = False):
        if not self.connected:
            self.connect()
        cs = self.ctx.cursor()
        try:
            cs.execute(query)
        except ProgrammingError as e:
            print(f"failed query:\n{query}")
            if "does not exist" in str(e) or "Insufficient privileges" in str(e):
                raise SnowflakeIntegrationException(
                    f"{str(e)}\nPlease ensure the role {self.role} "
                    f"is granted access to this table"
                )
            raise e
        finally:
            cs.close()
            if not keep_alive:
                self.close()

    def get_rows(self, query, keep_alive: bool = False):
        if not self.connected:
            self.connect()
        cs = self.ctx.cursor()
        try:
            cs.execute(query)
            return cs.fetchall()
        except ProgrammingError as e:
            if "does not exist" in str(e) or "Insufficient privileges" in str(e):
                print(f"Query could not be performed: {query}")
                raise SnowflakeIntegrationException(
                    f"{str(e)}\nPlease ensure the {self.role} "
                    f"is granted access to this table "
                )
            raise e
        finally:
            cs.close()
            if not keep_alive:
                self.close()

    def close(self):
        self.ctx.close()
        self.connected = False

    def replicate_table_schema(
        self,
        database: str,
        schema: str,
        table: str,
        column_definitions: List,
        keep_alive: bool = False,
    ):
        # get the current list of tables to see if the provided one already exists
        rows = self.get_rows(
            query=f"show tables in schema {database}.{schema};", keep_alive=True
        )
        if table not in [row[1] for row in rows]:
            snowflake_column_definitions = ", ".join(
                f"{c['name']} {c['type']}" for c in column_definitions
            )
            self.execute(
                query=f"CREATE OR REPLACE TABLE {database}.{schema}.{table} ({snowflake_column_definitions});",
                keep_alive=True,
            )
        else:
            current_columns = self.get_rows(
                query=f"show columns in table {database}.{schema}.{table};",
                keep_alive=True,
            )
            column_definitions_map = {
                str(c["name"]).lower(): c for c in column_definitions
            }
            new_column_names = [str(c["name"]).lower() for c in column_definitions]

            # Step 1 - Add missing columns by name
            current_column_names = [str(c[2]).lower() for c in current_columns]
            columns_to_add = [
                f"{str(c['name']).lower()} {c['type']}"
                for c in column_definitions
                if str(c["name"]).lower() not in current_column_names
            ]
            for c in columns_to_add:
                self.execute(
                    query=f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {c};",
                    keep_alive=True,
                )

            # Step 2 - Drop deleted columns
            columns_to_drop = [
                str(c[2]).lower()
                for c in current_columns
                if str(c[2].lower()) not in new_column_names
            ]
            for c in columns_to_drop:
                self.execute(
                    query=f"ALTER TABLE {database}.{schema}.{table} DROP COLUMN {c};",
                    keep_alive=True,
                )

            # Step 3 - Drop and re-add columns that changed type
            columns_to_drop_retype = [
                str(c[2]).lower()
                for c in current_columns
                if json.loads(c[3])["type"]
                != column_definitions_map[c[2].lower()]["type"]
            ]
            for c in columns_to_drop_retype:
                self.execute(
                    query=f"ALTER TABLE {database}.{schema}.{table} DROP COLUMN {c};",
                    keep_alive=True,
                )

            columns_to_add_retype = [
                f"{c['name']} {c['type']}"
                for c in column_definitions
                if str(c["name"]).lower() in columns_to_drop_retype
            ]
            for c in columns_to_add_retype:
                self.execute(
                    query=f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {c};",
                    keep_alive=True,
                )
        if not keep_alive:
            self.close()
