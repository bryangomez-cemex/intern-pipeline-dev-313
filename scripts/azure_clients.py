import os
import struct

import pyodbc
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential, ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient

from app_config import CONFIG


SQL_COPT_SS_ACCESS_TOKEN = 1256
SQL_SCOPE = "https://database.windows.net/.default"


def get_blob_service_client():
    if not CONFIG.azure_storage_connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing from environment.")

    return BlobServiceClient.from_connection_string(
        CONFIG.azure_storage_connection_string
    )


def _get_sql_credential():
    if CONFIG.azure_sql_auth_mode == "managed_identity":
        return ManagedIdentityCredential()

    if CONFIG.azure_sql_auth_mode == "default":
        return DefaultAzureCredential(exclude_interactive_browser_credential=False)

    return InteractiveBrowserCredential()


def get_sql_connection():
    if not CONFIG.azure_sql_server:
        raise ValueError("AZURE_SQL_SERVER is missing from environment.")

    if not CONFIG.azure_sql_database:
        raise ValueError("AZURE_SQL_DATABASE is missing from environment.")

    # SQL username/password auth — used when AZURE_SQL_AUTH_MODE=sql_password
    # or when AZURE_SQL_CONNECTION_STRING is a full ADO/ODBC connection string.
    if CONFIG.azure_sql_auth_mode == "sql_password":
        sql_user = os.environ.get("AZURE_SQL_USERNAME")
        sql_pass = os.environ.get("AZURE_SQL_PASSWORD")
        if not sql_user or not sql_pass:
            raise ValueError(
                "AZURE_SQL_AUTH_MODE=sql_password requires AZURE_SQL_USERNAME and AZURE_SQL_PASSWORD."
            )
        connection_string = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER=tcp:{CONFIG.azure_sql_server},1433;"
            f"DATABASE={CONFIG.azure_sql_database};"
            f"UID={sql_user};"
            f"PWD={sql_pass};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=60;"
        )
        return pyodbc.connect(connection_string)

    # Also support a pre-built ODBC/ADO connection string (used by GitHub Actions).
    conn_str_env = os.environ.get("AZURE_SQL_CONNECTION_STRING")
    if conn_str_env:
        return pyodbc.connect(conn_str_env)

    token = _get_sql_credential().get_token(SQL_SCOPE).token
    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{CONFIG.azure_sql_server},1433;"
        f"DATABASE={CONFIG.azure_sql_database};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )

    return pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
    )
