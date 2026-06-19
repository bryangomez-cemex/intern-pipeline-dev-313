import os
import shutil
from datetime import datetime, UTC
from pathlib import Path

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
RAW_UPLOADS_CONTAINER = os.getenv("RAW_UPLOADS_CONTAINER", "raw-uploads")

INTAKE_FOLDER = Path("intake_files")
PROCESSED_FOLDER = Path("intake_files_processed")
FAILED_FOLDER = Path("intake_files_failed")

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".csv", ".png", ".jpg", ".jpeg"}


# ============================================================
# HELPERS
# ============================================================

def utc_timestamp():
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def get_blob_service_client():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing from .env")

    return BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    )


def ensure_folders():
    INTAKE_FOLDER.mkdir(exist_ok=True)
    PROCESSED_FOLDER.mkdir(exist_ok=True)
    FAILED_FOLDER.mkdir(exist_ok=True)


def build_blob_name(file_path):
    timestamp = utc_timestamp()
    clean_name = file_path.name.replace(" ", "_")
    return f"local_intake/{timestamp}_{clean_name}"


def upload_file(file_path):
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(RAW_UPLOADS_CONTAINER)

    blob_name = build_blob_name(file_path)

    with open(file_path, "rb") as file_data:
        container_client.upload_blob(
            name=blob_name,
            data=file_data,
            overwrite=True
        )

    return blob_name


# ============================================================
# MAIN
# ============================================================

def intake_local_folder():
    ensure_folders()

    files = [
        file_path for file_path in INTAKE_FOLDER.iterdir()
        if file_path.is_file()
    ]

    if not files:
        print("No files found in intake_files.")
        return []

    uploaded_blobs = []

    for file_path in files:
        try:
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                print(f"Skipping unsupported file: {file_path.name}")
                shutil.move(str(file_path), FAILED_FOLDER / file_path.name)
                continue

            blob_name = upload_file(file_path)
            uploaded_blobs.append(blob_name)

            shutil.move(str(file_path), PROCESSED_FOLDER / file_path.name)

            print(f"Uploaded: {file_path.name}")
            print(f"Blob path: {blob_name}")

        except Exception as e:
            print(f"Failed to upload: {file_path.name}")
            print(e)

            try:
                shutil.move(str(file_path), FAILED_FOLDER / file_path.name)
            except Exception:
                pass

    print(f"Local intake completed. Uploaded files: {len(uploaded_blobs)}")

    return uploaded_blobs


if __name__ == "__main__":
    intake_local_folder()