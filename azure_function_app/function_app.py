import logging
import os
import sys
from pathlib import Path

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
