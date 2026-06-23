import os
import imaplib
import email
from email.header import decode_header
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

IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USERNAME = os.getenv("IMAP_USERNAME")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
INTAKE_EMAIL_FOLDER = os.getenv("INTAKE_EMAIL_FOLDER", "INBOX")

# SAFETY: only process emails whose subject contains this tag. This keeps the
# intake from sweeping an entire personal inbox — it only picks up messages the
# sender deliberately marked for the pipeline. Set to empty to disable (NOT
# recommended on a shared/personal inbox).
INTAKE_SUBJECT_TAG = os.getenv("INTAKE_SUBJECT_TAG", "[INTERN]").strip()
# Hard cap on emails handled per run, as a backstop against a bad search.
MAX_EMAILS_PER_RUN = int(os.getenv("INTAKE_MAX_EMAILS_PER_RUN", "25"))

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".csv", ".png", ".jpg", ".jpeg"}

DOWNLOAD_FOLDER = Path("data/email_intake_downloads")


# ============================================================
# HELPERS
# ============================================================

def utc_timestamp():
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def safe_text(value):
    if value is None:
        return ""

    return (
        str(value)
        .replace("\xa0", " ")
        .replace("\u200b", "")
        .strip()
    )


def decode_email_header(value):
    if not value:
        return ""

    decoded_parts = decode_header(value)
    result = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part

    return safe_text(result)


def get_blob_service_client():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing from .env")

    return BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    )


def build_blob_name(filename, email_uid):
    timestamp = utc_timestamp()
    clean_name = filename.replace(" ", "_")
    return f"email_intake/{timestamp}_uid_{email_uid}_{clean_name}"


def upload_file_to_blob(local_path, blob_name):
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(RAW_UPLOADS_CONTAINER)

    with open(local_path, "rb") as file_data:
        container_client.upload_blob(
            name=blob_name,
            data=file_data,
            overwrite=True
        )

    return blob_name


def connect_imap():
    if not IMAP_USERNAME:
        raise ValueError("IMAP_USERNAME is missing from .env")

    if not IMAP_PASSWORD:
        raise ValueError("IMAP_PASSWORD is missing from .env")

    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    mail.login(
        safe_text(IMAP_USERNAME),
        safe_text(IMAP_PASSWORD).replace(" ", "")
    )

    return mail


# ============================================================
# MAIN
# ============================================================

def intake_gmail_attachments():
    DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    mail = connect_imap()

    uploaded_blobs = []

    try:
        mail.select(INTAKE_EMAIL_FOLDER)

        # Only unread messages, and (by default) only those whose subject carries
        # the pipeline tag — so a busy personal inbox is never swept wholesale.
        if INTAKE_SUBJECT_TAG:
            status, data = mail.search(None, "UNSEEN", "SUBJECT", f'"{INTAKE_SUBJECT_TAG}"')
            scope = f'unread emails with subject containing "{INTAKE_SUBJECT_TAG}"'
        else:
            status, data = mail.search(None, "UNSEEN")
            scope = "unread emails"

        if status != "OK":
            print("Could not search inbox.")
            return []

        email_ids = data[0].split()

        if not email_ids:
            print(f"No {scope} found.")
            return []

        if len(email_ids) > MAX_EMAILS_PER_RUN:
            print(f"{len(email_ids)} matched; capping to the {MAX_EMAILS_PER_RUN} most recent this run.")
            email_ids = email_ids[-MAX_EMAILS_PER_RUN:]

        print(f"Matched {scope}: {len(email_ids)}")

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            if status != "OK":
                print(f"Could not fetch email ID: {email_id}")
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_email_header(msg.get("Subject"))
            sender = decode_email_header(msg.get("From"))

            print("----------------------------------------")
            print(f"Email ID: {email_id.decode()}")
            print(f"From: {sender}")
            print(f"Subject: {subject}")

            attachments_found = 0

            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition") or "")

                if "attachment" not in content_disposition.lower():
                    continue

                filename = part.get_filename()

                if not filename:
                    continue

                filename = decode_email_header(filename)
                extension = Path(filename).suffix.lower()

                if extension not in ALLOWED_EXTENSIONS:
                    print(f"Skipping unsupported attachment: {filename}")
                    continue

                attachments_found += 1

                local_path = DOWNLOAD_FOLDER / filename

                payload = part.get_payload(decode=True)

                with open(local_path, "wb") as file:
                    file.write(payload)

                blob_name = build_blob_name(
                    filename=filename,
                    email_uid=email_id.decode()
                )

                upload_file_to_blob(local_path, blob_name)
                uploaded_blobs.append(blob_name)

                print(f"Uploaded attachment: {filename}")
                print(f"Blob path: {blob_name}")

            if attachments_found == 0:
                print("No allowed attachments found.")

            # Mark email as seen only after processing attempt
            mail.store(email_id, "+FLAGS", "\\Seen")

        print("----------------------------------------")
        print(f"Gmail intake completed. Uploaded files: {len(uploaded_blobs)}")

        return uploaded_blobs

    finally:
        mail.logout()


if __name__ == "__main__":
    intake_gmail_attachments()