import json
import base64
import subprocess
import sys


RESOURCE_GROUP = "rg-intern-pipeline-dev"
FUNCTION_APP = "mex-intern-pipeline-func-win"
CONTAINER_NAME = "aci-sql-verify-20260625"


def az(args):
    return subprocess.run(
        ["az", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def az_out(args):
    result = az(args)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def get_settings():
    raw = az_out(
        [
            "functionapp",
            "config",
            "appsettings",
            "list",
            "--resource-group",
            RESOURCE_GROUP,
            "--name",
            FUNCTION_APP,
            "--query",
            "[].{name:name,value:value}",
            "--output",
            "json",
        ]
    )
    return {item["name"]: item.get("value", "") for item in json.loads(raw)}


def parse_connection_parts(settings):
    raw = settings.get("AZURE_SQL_CONNECTION_STRING", "")
    parts = {}
    for part in raw.split(";"):
        if "=" in part:
            key, value = part.split("=", 1)
            parts[key.strip().lower()] = value.strip()

    server = (
        settings.get("AZURE_SQL_SERVER")
        or parts.get("server")
        or parts.get("data source")
        or parts.get("erver")
        or ""
    )
    server = server.replace("tcp:", "").split(",")[0]
    database = (
        settings.get("AZURE_SQL_DATABASE")
        or parts.get("database")
        or parts.get("initial catalog")
    )
    username = parts.get("uid") or parts.get("user id")
    password = parts.get("pwd") or parts.get("password")
    return server, database, username, password


def main():
    settings = get_settings()
    server, database, username, password = parse_connection_parts(settings)
    query = (
        "SET NOCOUNT ON; "
        "SELECT 'dbo_tables' AS metric, COUNT(*) AS value FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo'); "
        "SELECT 'dbo_views' AS metric, COUNT(*) AS value FROM sys.views WHERE schema_id = SCHEMA_ID('dbo'); "
        "SELECT required_view FROM (VALUES "
        "('vw_powerbi_dashboard_kpis'),('vw_powerbi_vp_summary'),('vw_powerbi_location_summary'),"
        "('vw_powerbi_contract_risk'),('vw_powerbi_document_status'),('vw_powerbi_document_summary'),"
        "('vw_powerbi_hr_action_queue'),('vw_powerbi_vacantes'),('vw_powerbi_costos_practicantes'),"
        "('vw_powerbi_vp_capacity')) AS req(required_view) "
        "WHERE OBJECT_ID('dbo.' + required_view, 'V') IS NULL;"
    )
    encoded_query = base64.b64encode(query.encode("utf-8")).decode("ascii")
    command = (
        f"printf %s {encoded_query} | base64 -d > /tmp/verify.sql; "
        "/opt/mssql-tools/bin/sqlcmd "
        '-S "$SQLSERVER" -d "$SQLDB" -U "$SQLUSER" -P "$SQLPASSWORD" '
        "-b -i /tmp/verify.sql"
    )
    args = [
        "container",
        "create",
        "--resource-group",
        RESOURCE_GROUP,
        "--name",
        CONTAINER_NAME,
        "--image",
        "mcr.microsoft.com/mssql-tools",
        "--restart-policy",
        "Never",
        "--os-type",
        "Linux",
        "--cpu",
        "1",
        "--memory",
        "1",
        "--environment-variables",
        f"SQLSERVER={server}",
        f"SQLDB={database}",
        f"SQLUSER={username}",
        "--secure-environment-variables",
        f"SQLPASSWORD={password}",
        "--command-line",
        f"/bin/bash -lc {command!r}",
        "--output",
        "none",
    ]
    result = az(args)
    if result.returncode:
        print(result.stderr.replace(password or "", "<sql_password>")[:4000])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
