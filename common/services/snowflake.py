import base64
import json
import re
from typing import List

import snowflake.connector
from snowflake.connector.errors import ProgrammingError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from common.models.firestore.connections import Authorization
from common.services.base import BaseService
from common.services.constants import SNOWFLAKE_RESERVED_KEYWORDS
from common.logging.client import Logger
from common.models.snowflake.replication import ReplicationSummary

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
        cloud_platform: str,
        username: str,
        role: str,
        warehouse: str,
        region: str | None = None,
        redirect_uri: str | None = None,
        access_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        password: str | None = None,
        paramstyle: str | None = None,
        logger: Logger | None = None,
        passcode: str | None = None,
        private_key_file: str | None = None,
        private_key_file_pwd: str | None = None,
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
        self.passcode = passcode
        self.private_key_file = private_key_file

        self.private_key_file_pwd = private_key_file_pwd
        if region:
            self.account_url = f"{self.account_url}.{region}"
            if region.lower() not in URL_CLOUD_PLATFORMS:
                self.account_url = f"{self.account_url}.{cloud_platform.lower()}"
        self.connected = False
        self.ctx = None

    def connect(self):
        try:
            if self.private_key_file and self.private_key_file_pwd:
                p_key = serialization.load_pem_private_key(
                    bytes(self.private_key_file, "utf-8"),
                    password=bytes(self.private_key_file_pwd, "utf-8"),
                    backend=default_backend(),
                )

                pkb = p_key.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                self.ctx = snowflake.connector.connect(
                    user=self.username,
                    account=self.account_url,
                    authenticator="SNOWFLAKE_JWT",
                    private_key=pkb,
                    warehouse=self.warehouse,
                    role=self.role,
                )
            elif self.access_token:
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
                    passcode=self.passcode,
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
        response_json: dict = r.json()
        if "error" in response_json:
            raise SnowflakeIntegrationException(
                f"Error: {response_json['error']}, Message: {response_json['message']}"
            )
        authorization = Authorization.model_validate(response_json)
        self.access_token = authorization.access_token
        return authorization

    def execute(self, query, keep_alive: bool = False):
        if not self.connected:
            self.connect()
        if not self.ctx:
            raise SnowflakeIntegrationException("Not connected to Snowflake")
        cs = self.ctx.cursor()
        try:
            cs.execute(query)
        except ProgrammingError as e:
            self.logger.error(f"Query could not be performed: {query}")
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
        if not self.ctx:
            raise SnowflakeIntegrationException("Not connected to Snowflake")
        cs = self.ctx.cursor()
        try:
            cs.execute(query)
            return cs.fetchall()
        except ProgrammingError as e:
            self.logger.error(f"Query could not be performed: {query}")
            if "does not exist" in str(e) or "Insufficient privileges" in str(e):
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
        if not self.ctx:
            raise SnowflakeIntegrationException("Not connected to Snowflake")
        self.ctx.close()
        self.connected = False

    def _quote_column_name(self, column_name: str) -> str:
        """Quote column name if it contains special characters or is a reserved word."""
        # Remove existing quotes if present
        name = str(column_name).strip('"')

        # Check if the column name needs quoting
        if (
            re.search(r"[^a-zA-Z0-9_]", name)  # Contains special chars or spaces
            or name[0].isdigit()  # Starts with digit
            or name.upper() in SNOWFLAKE_RESERVED_KEYWORDS
        ):  # Is a reserved keyword
            return f'"{name}"'
        return name

    def _types_are_equivalent(self, snowflake_type: str, expected_type: str) -> bool:
        """Check if Snowflake type and expected type are equivalent."""
        sf_type = snowflake_type.upper()
        exp_type = expected_type.upper()

        # Direct match
        if sf_type == exp_type:
            return True

        # String types - all equivalent
        string_types = {"VARCHAR", "CHAR", "CHARACTER", "STRING", "TEXT"}
        if sf_type in string_types and exp_type in string_types:
            return True

        # Numeric types - Snowflake uses FIXED internally for most numeric types
        if sf_type == "FIXED":
            numeric_types = {
                "NUMBER",
                "DECIMAL",
                "NUMERIC",
                "INT",
                "INTEGER",
                "BIGINT",
                "SMALLINT",
                "TINYINT",
                "BYTEINT",
            }
            if any(exp_type.startswith(t) for t in numeric_types):
                return True

        # Float types - Snowflake displays as FLOAT but stores as DOUBLE
        if sf_type in {"FLOAT", "DOUBLE"}:
            float_types = {
                "FLOAT",
                "FLOAT4",
                "FLOAT8",
                "DOUBLE",
                "DOUBLE PRECISION",
                "REAL",
            }
            if exp_type in float_types:
                return True

        # Binary types
        if sf_type == "BINARY" and exp_type == "VARBINARY":
            return True
        if sf_type == "VARBINARY" and exp_type == "BINARY":
            return True

        # Timestamp types
        if sf_type == "TIMESTAMP_NTZ" and exp_type in {"TIMESTAMP", "DATETIME"}:
            return True
        if sf_type == "TIMESTAMP" and exp_type in {"TIMESTAMP_NTZ", "DATETIME"}:
            return True

        return False

    def replicate_table_schema(
        self,
        database: str,
        schema: str,
        table: str,
        column_definitions: List,
        keep_alive: bool = False,
    ) -> ReplicationSummary:
        # get the current list of tables to see if the provided one already exists
        rows = self.get_rows(
            query=f"show tables in schema {database}.{schema};", keep_alive=True
        )
        if table.strip().lower() not in [row[1].strip().lower() for row in rows]:
            snowflake_column_definitions = ", ".join(
                f"{self._quote_column_name(c['name'])} {c['type']}"
                for c in column_definitions
            )
            self.logger.info(
                f"Creating table {database}.{schema}.{table}",
                labels={
                    "database": database,
                    "schema": schema,
                    "table": table,
                    "snowflake_column_definitions": snowflake_column_definitions,
                },
            )
            self.execute(
                query=f"CREATE OR REPLACE TABLE {database}.{schema}.{table} ({snowflake_column_definitions});",
                keep_alive=True,
            )
            return ReplicationSummary(columns_added=len(column_definitions))
        else:
            current_columns = self.get_rows(
                query=f"show columns in table {database}.{schema}.{table};",
                keep_alive=True,
            )
            column_definitions_map = {
                str(c["name"]).lower().strip('"'): c for c in column_definitions
            }
            new_column_names = [
                str(c["name"]).lower().strip('"') for c in column_definitions
            ]

            # Step 1 - Add missing columns by name
            current_column_names = [str(c[2]).lower() for c in current_columns]
            columns_to_add = [
                f"{self._quote_column_name(c['name'])} {c['type']}"
                for c in column_definitions
                if str(c["name"]).lower().strip('"') not in current_column_names
            ]
            if columns_to_add:
                self.logger.info(
                    f"Adding columns to {database}.{schema}.{table}",
                    labels={
                        "database": database,
                        "schema": schema,
                        "table": table,
                        "columns_to_add": str(columns_to_add),
                    },
                )
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
            if columns_to_drop:
                self.logger.info(
                    f"Dropping columns from {database}.{schema}.{table}",
                    labels={
                        "database": database,
                        "schema": schema,
                        "table": table,
                        "columns_to_drop": str(columns_to_drop),
                    },
                )
                for c in columns_to_drop:
                    self.execute(
                        query=f"ALTER TABLE {database}.{schema}.{table} DROP COLUMN {self._quote_column_name(c)};",
                        keep_alive=True,
                    )

            columns_to_drop_retype = [
                str(c[2]).lower()
                for c in current_columns
                if str(c[2]).lower().strip('"') in column_definitions_map
                and not self._types_are_equivalent(
                    json.loads(c[3])["type"],
                    column_definitions_map[str(c[2]).lower().strip('"')]["type"],
                )
            ]
            if columns_to_drop_retype:
                self.logger.info(
                    f"Dropping and re-adding columns from {database}.{schema}.{table}",
                    labels={
                        "database": database,
                        "schema": schema,
                        "table": table,
                        "columns_to_drop_retype": str(columns_to_drop_retype),
                    },
                )
                for c in columns_to_drop_retype:
                    self.execute(
                        query=f"ALTER TABLE {database}.{schema}.{table} DROP COLUMN {self._quote_column_name(c)};",
                        keep_alive=True,
                    )

            columns_to_add_retype = [
                f"{self._quote_column_name(c['name'])} {c['type']}"
                for c in column_definitions
                if str(c["name"]).lower().strip('"') in columns_to_drop_retype
            ]
            if columns_to_add_retype:
                self.logger.info(
                    f"Adding columns to {database}.{schema}.{table}",
                    labels={
                        "database": database,
                        "schema": schema,
                        "table": table,
                        "columns_to_add_retype": str(columns_to_add_retype),
                    },
                )
                for c in columns_to_add_retype:
                    self.execute(
                        query=f"ALTER TABLE {database}.{schema}.{table} ADD COLUMN {c};",
                        keep_alive=True,
                    )
        if not keep_alive:
            self.close()
        return ReplicationSummary(
            columns_added=len(columns_to_add),
            columns_dropped=len(columns_to_drop),
            columns_retyped=len(columns_to_add_retype),
        )
