import json
import subprocess
import sys


RESOURCE_GROUP = "rg-intern-pipeline-dev"
FUNCTION_APP = "mex-intern-pipeline-func-win"
STORAGE_ACCOUNT = "rginternpipelinedevb961"
FILE_SHARE = "sqlsetup5"
CONTAINER_NAME = "aci-sql-setup-20260625"


def az(args, **kwargs):
    return subprocess.run(
        ["az", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    )


def az_out(args):
    result = az(args)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def redact(text, secrets):
    redacted = text or ""
    for label, value in secrets.items():
        if value:
            redacted = redacted.replace(value, f"<{label}>")
    return redacted


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

    missing = [
        name
        for name, value in {
            "server": server,
            "database": database,
            "username": username,
            "password": password,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing SQL connection parts: {', '.join(missing)}")

    return server, database, username, password


def main():
    storage_key = az_out(
        [
            "storage",
            "account",
            "keys",
            "list",
            "--resource-group",
            RESOURCE_GROUP,
            "--account-name",
            STORAGE_ACCOUNT,
            "--query",
            "[0].value",
            "--output",
            "tsv",
        ]
    )
    settings = get_settings()
    server, database, username, password = parse_connection_parts(settings)
    secrets = {"storage_key": storage_key, "sql_password": password}

    command = (
        "set -euo pipefail; "
        "for f in /mnt/sql/*.sql; do "
        'echo "Running $(basename "$f")"; '
        '/opt/mssql-tools/bin/sqlcmd -S "$SQLSERVER" -d "$SQLDB" '
        '-U "$SQLUSER" -P "$SQLPASSWORD" -b -i "$f"; '
        "done; "
        'echo "SQL_SETUP_DONE"'
    )

    create_args = [
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
        "--azure-file-volume-account-name",
        STORAGE_ACCOUNT,
        "--azure-file-volume-account-key",
        storage_key,
        "--azure-file-volume-share-name",
        FILE_SHARE,
        "--azure-file-volume-mount-path",
        "/mnt/sql",
        "--environment-variables",
        f"SQLSERVER={server}",
        f"SQLDB={database}",
        f"SQLUSER={username}",
        "--secure-environment-variables",
        f"SQLPASSWORD={password}",
        "--command-line",
        f"/bin/bash -lc {command!r}",
        "--output",
        "json",
    ]
    result = az(create_args)
    print(f"container_create_returncode={result.returncode}")
    if result.stdout:
        print(redact(result.stdout[:3000], secrets))
    if result.stderr:
        print(redact(result.stderr[:4000], secrets))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
