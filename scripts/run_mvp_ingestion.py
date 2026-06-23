import os
import sys
from datetime import datetime
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

from pipeline_service import process_blob_by_name

CONTAINER = os.getenv("RAW_UPLOADS_CONTAINER", "raw-uploads")
PREFIX = os.getenv("MVP_PREFIX", "")

ALLOWED_EXTENSIONS = (".xlsx", ".csv", ".pdf", ".png", ".jpg", ".jpeg")
SKIP_PREFIXES = ("archive/", "processed/", "failed/", "error-reports/")


def main():
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or os.environ.get("PIPELINE_STORAGE_CONN")
    if not conn:
        raise SystemExit("Missing storage connection string")

    service = BlobServiceClient.from_connection_string(conn)
    container = service.get_container_client(CONTAINER)

    print(f"Starting ingestion: {datetime.now()}")
    print(f"Container: {CONTAINER}")
    print(f"Prefix: {PREFIX or '(all files)'}")

    processed = 0
    failed = 0
    skipped_missing = 0

    for blob in container.list_blobs(name_starts_with=PREFIX):
        name = blob.name

        if name.endswith("/") or name.startswith(SKIP_PREFIXES):
            continue

        if not name.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        print(f"\nProcessing: {name}")

        try:
            result = process_blob_by_name(
                source_container=CONTAINER,
                source_blob_name=name,
                run_type="github_actions_mvp",
            )
            print(f"OK: {result}")
            processed += 1
        except ResourceNotFoundError:
            # The blob was deleted between listing and processing — typically a
            # concurrent run that already archived it, or an external delete.
            # This is benign: skip it rather than counting a hard failure.
            print(f"SKIPPED (blob no longer exists): {name}")
            skipped_missing += 1
        except Exception as e:
            print(f"FAILED: {name}")
            print(type(e).__name__, str(e))
            failed += 1

    print("\nDONE")
    print(f"Processed: {processed}")
    print(f"Skipped (missing): {skipped_missing}")
    print(f"Failed: {failed}")

    # Validation failures are EXPECTED and are written to SQL as success.
    # A real infrastructure failure (bad connection string, SQL unreachable,
    # driver missing) should fail the CI job so it is visible. A blob that
    # merely failed business validation must NOT fail the job.
    if failed > 0:
        raise SystemExit(f"{failed} blob(s) hit an unexpected processing error.")


if __name__ == "__main__":
    main()
