import logging
import os
import sys
from pathlib import Path
import re

import azure.functions as func


APP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = APP_ROOT.parent
FUNCTION_SCRIPTS_DIR = APP_ROOT / "scripts"
REPO_SCRIPTS_DIR = REPO_ROOT / "scripts"

for path in (str(FUNCTION_SCRIPTS_DIR), str(REPO_SCRIPTS_DIR), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


# v2 programming model: a single FunctionApp instance that the worker indexes.
# Requires the app setting AzureWebJobsFeatureFlags=EnableWorkerIndexing.
app = func.FunctionApp()


def should_ignore_blob(name):
    if not name or name.endswith("/"):
        return True

    ignored_prefixes = (
        "archive/",
        "processed/",
        "failed/",
        "error-reports/",
        ".",
    )

    return name.startswith(ignored_prefixes)


@app.blob_trigger(
    arg_name="inputblob",
    path="raw-uploads/{name}",
    connection="AZURE_STORAGE_CONNECTION_STRING",
    source=func.BlobSource.EVENT_GRID,
)
def process_raw_upload(inputblob: func.InputStream):
    # inputblob.name is the full path including the container, e.g.
    # "raw-uploads/unknown/2026/06/22/file.csv" — strip the container segment.
    blob_name = inputblob.name.split("/", 1)[1] if "/" in inputblob.name else inputblob.name
    source_container = os.getenv("RAW_UPLOADS_CONTAINER", "raw-uploads")

    if should_ignore_blob(blob_name):
        logging.info("Ignoring blob trigger for %s", blob_name)
        return

    logging.info("Processing blob trigger for %s/%s", source_container, blob_name)

    try:
        from pipeline_service import process_blob_by_name

        result = process_blob_by_name(
            source_container=source_container,
            source_blob_name=blob_name,
            run_type="blob_trigger",
        )
        logging.info("Pipeline completed for %s: %s", blob_name, result)
    except Exception:
        logging.exception("Pipeline failed for triggered blob %s", blob_name)
        raise


SQL_SETUP_ORDER = [
    "00_create_core_legacy_tables.sql",
    "00_create_dim_interns.sql",
    "create_full_mvp_pipeline.sql",
    "fix_file_id_source_file_id_compatibility.sql",
    "seed_pipeline_validation_rules.sql",
    "2026-06_package1_document_requirements.sql",
    "2026-06_resolve_stale_missing_items.sql",
    "add_corporate_column_aliases.sql",
    "create_matching_engine_v1.sql",
    "create_business_powerbi_views.sql",
    "2026-06_onboarding_schema.sql",
    "2026-06_schema_simplification.sql",
    "2026-06_powerbi_no_dax_views.sql",
    "2026-06_powerbi_refinements.sql",
    "2026-06_open_positions.sql",
    "2026-06_cost_columns.sql",
    "2026-06_costos_por_compania.sql",
]


def split_sql_batches(script_text):
    batches = []
    current = []
    for line in script_text.splitlines():
        if re.match(r"^\s*GO\s*$", line, re.IGNORECASE):
            batch = "\n".join(current).strip()
            if batch:
                batches.append(batch)
            current = []
            continue
        current.append(line)

    batch = "\n".join(current).strip()
    if batch:
        batches.append(batch)
    return batches


def run_database_setup():
    sql_dir = APP_ROOT / "sql"
    results = []

    from azure_clients import get_sql_connection

    with get_sql_connection() as conn:
        conn.autocommit = True
        cursor = conn.cursor()
        for script_name in SQL_SETUP_ORDER:
            script_path = sql_dir / script_name
            if not script_path.exists():
                raise FileNotFoundError(f"Missing SQL setup script: {script_name}")

            batches = split_sql_batches(script_path.read_text(encoding="utf-8"))
            for batch in batches:
                cursor.execute(batch)

            results.append({"script": script_name, "batches": len(batches)})

    return results


@app.route(route="admin/setup-database", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def setup_database(req: func.HttpRequest) -> func.HttpResponse:
    if os.getenv("ENABLE_ADMIN_SQL_SETUP", "").lower() not in {"1", "true", "yes"}:
        return func.HttpResponse(
            '{"error":"admin SQL setup is disabled"}',
            status_code=403,
            mimetype="application/json",
        )

    try:
        import json

        return func.HttpResponse(
            json.dumps({"status": "ok", "scripts": run_database_setup()}),
            status_code=200,
            mimetype="application/json",
        )
    except Exception as exc:
        logging.exception("Admin SQL setup failed")
        import json

        return func.HttpResponse(
            json.dumps({"status": "error", "error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )


@app.schedule(
    schedule="0 0 5 1 1 *",
    arg_name="setup_timer",
    run_on_startup=True,
    use_monitor=False,
)
def setup_database_on_startup(setup_timer: func.TimerRequest):
    if os.getenv("ENABLE_ADMIN_SQL_SETUP", "").lower() not in {"1", "true", "yes"}:
        logging.info("Admin SQL setup timer skipped because ENABLE_ADMIN_SQL_SETUP is disabled")
        return

    logging.warning("Admin SQL setup timer is enabled; running database setup scripts")
    results = run_database_setup()
    logging.warning("Admin SQL setup timer completed: %s", results)
