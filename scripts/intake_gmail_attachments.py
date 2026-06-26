import os
import imaplib
import email
import re
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

# Optional subject filter. Production should normally leave this empty because
# subjects vary by process; classification uses attachments, email metadata, body
# fields, and requisition IDs instead of a fixed subject tag.
INTAKE_SUBJECT_TAG = os.getenv("INTAKE_SUBJECT_TAG", "").strip()
# Hard cap on emails handled per run, as a backstop against a bad search.
MAX_EMAILS_PER_RUN = int(os.getenv("INTAKE_MAX_EMAILS_PER_RUN", "25"))

ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".docx"}
REQ_RE = re.compile(r"REQ-\d{4}-\d{3,}", re.IGNORECASE)

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


def upload_file_to_blob(local_path, blob_name, metadata=None):
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(RAW_UPLOADS_CONTAINER)

    with open(local_path, "rb") as file_data:
        container_client.upload_blob(
            name=blob_name,
            data=file_data,
            overwrite=True,
            metadata=metadata or {},
        )

    return blob_name


def extract_reqid(*texts):
    for text in texts:
        match = REQ_RE.search(text or "")
        if match:
            return match.group(0).upper()
    return ""


def parse_sender_and_reqid(sender_header, *texts):
    """Extract a clean sender email and any REQ-YYYY-#### tag from email text."""
    from email.utils import parseaddr

    sender_email = parseaddr(sender_header or "")[1] or (sender_header or "")
    return sender_email, extract_reqid(*texts)


def get_email_body(msg):
    """Return the plain-text body of an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "")
            if part.get_content_type() == "text/plain" and "attachment" not in disp.lower():
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore")
                except Exception:
                    continue
        return ""
    try:
        return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "ignore")
    except Exception:
        return ""


def _strip_accents(value):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", value or "") if not unicodedata.combining(c)).lower().strip()


# Fields the intern returns in the body of the Welcome 1 reply.
BODY_LABELS = [
    (["nombre completo"], "nombre_completo"),
    (["como te gusta que te digan", "apodo", "como te dicen"], "apodo"),
    (["fecha de nacimiento"], "fecha_nacimiento"),
    (["fecha estimada de graduacion", "fecha de graduacion", "graduacion"], "fecha_graduacion"),
    (["telefono celular", "telefono", "celular"], "telefono"),
    (["enlace a tu perfil de linkedin", "perfil de linkedin", "linkedin"], "linkedin"),
    (["contacto de emergencia", "emergencia"], "contacto_emergencia"),
]


def parse_intern_email_body(text):
    """Extract intern-supplied Label: value fields from an email body."""
    out = {}
    for raw in (text or "").splitlines():
        if ":" not in raw:
            continue
        label, _, value = raw.partition(":")
        ln = _strip_accents(label).replace("¿", "").replace("?", "").strip()
        value = value.strip()
        if not value:
            continue
        for keys, field in BODY_LABELS:
            if field not in out and any(k in ln for k in keys):
                out[field] = value[:200]
                break
    return out


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

        # Only unread messages. If INTAKE_SUBJECT_TAG is explicitly configured,
        # narrow to that tag; otherwise use attachments + metadata/body parsing.
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

            import json as _json
            email_body = get_email_body(msg)
            sender_email, requisition_id = parse_sender_and_reqid(sender, subject, email_body)
            body_fields = parse_intern_email_body(email_body)
            if body_fields:
                print(f"Body fields parsed: {list(body_fields.keys())}")
            base_blob_metadata = {
                "sender_email": sender_email,
                "email_subject": (subject or "")[:200],
                "requisition_id": requisition_id,
                "body_fields": _json.dumps(body_fields) if body_fields else "",
            }

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

                blob_metadata = dict(base_blob_metadata)
                blob_metadata["requisition_id"] = extract_reqid(
                    blob_metadata.get("requisition_id"),
                    subject,
                    email_body,
                    filename,
                    blob_name,
                )

                upload_file_to_blob(local_path, blob_name, metadata=blob_metadata)
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
