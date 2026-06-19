import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class AppConfig:
    azure_storage_connection_string: str | None
    raw_uploads_container: str
    error_reports_container: str
    archive_container: str
    azure_sql_server: str | None
    azure_sql_database: str | None
    azure_sql_auth_mode: str
    email_mode: str
    dev_email_override: str | None
    app_environment: str
    local_work_dir: str
    allowed_extensions: set[str]


def get_config() -> AppConfig:
    email_mode = os.getenv("EMAIL_MODE", "simulation").strip().lower()
    sql_auth_mode = os.getenv("AZURE_SQL_AUTH_MODE", "interactive").strip().lower()
    default_work_dir = "/tmp/intern-system-pipeline" if os.getenv("WEBSITE_SITE_NAME") else "data"

    return AppConfig(
        azure_storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        raw_uploads_container=os.getenv("RAW_UPLOADS_CONTAINER", "raw-uploads"),
        error_reports_container=os.getenv("ERROR_REPORTS_CONTAINER", "error-reports"),
        archive_container=os.getenv("ARCHIVE_CONTAINER", "archive"),
        azure_sql_server=os.getenv("AZURE_SQL_SERVER"),
        azure_sql_database=os.getenv("AZURE_SQL_DATABASE"),
        azure_sql_auth_mode=sql_auth_mode,
        email_mode=email_mode,
        dev_email_override=os.getenv("DEV_EMAIL_OVERRIDE"),
        app_environment=os.getenv("APP_ENV", "local").strip().lower(),
        local_work_dir=os.getenv("LOCAL_WORK_DIR", default_work_dir),
        allowed_extensions={"pdf", "xlsx", "csv", "png", "jpg", "jpeg"},
    )


CONFIG = get_config()
