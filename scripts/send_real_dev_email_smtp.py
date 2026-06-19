import os
import struct
import uuid
import smtplib
from email.message import EmailMessage
from pathlib import Path

import pyodbc
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential
from azure.storage.blob import BlobServiceClient


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
ERROR_REPORTS_CONTAINER = os.getenv("ERROR_REPORTS_CONTAINER", "error-reports")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
DEV_EMAIL_OVERRIDE = os.getenv("DEV_EMAIL_OVERRIDE")


# ============================================================
# SQL CONNECTION
# ============================================================

def get_sql_connection():
    credential = InteractiveBrowserCredential()
    token = credential.get_token("https://database.windows.net/.default").token

    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    SQL_COPT_SS_ACCESS_TOKEN = 1256

    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER=tcp:{SQL_SERVER},1433;"
        f"DATABASE={SQL_DATABASE};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=60;"
    )

    return pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
    )


# ============================================================
# BLOB STORAGE
# ============================================================

def get_blob_service_client():
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing from .env")

    return BlobServiceClient.from_connection_string(
        AZURE_STORAGE_CONNECTION_STRING
    )


def download_error_report_if_available(file_id):
    """
    Looks up fact_files using the communication file_id.
    If that file is in error-reports, download it locally and return the path.
    """
    if not file_id:
        return None

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT TOP 1
                original_file_name,
                blob_container,
                blob_path
            FROM fact_files
            WHERE file_id = ?
            """,
            file_id,
        )

        row = cursor.fetchone()

        if not row:
            return None

        original_file_name, blob_container, blob_path = row

        if blob_container != ERROR_REPORTS_CONTAINER:
            return None

        os.makedirs("data/email_attachments", exist_ok=True)
        local_path = os.path.join("data", "email_attachments", original_file_name)

        blob_service_client = get_blob_service_client()
        container_client = blob_service_client.get_container_client(blob_container)

        with open(local_path, "wb") as download_file:
            download_file.write(container_client.download_blob(blob_path).readall())

        return local_path

    finally:
        cursor.close()
        conn.close()


# ============================================================
# SQL COMMUNICATION FUNCTIONS
# ============================================================

def fetch_dev_simulated_communications(cursor):
    """
    For safety, only send communications that were already simulated.
    This prevents sending brand-new Prepared messages by accident.
    """
    cursor.execute(
        """
        SELECT TOP 5
            communication_id,
            email_type,
            sent_to,
            status,
            communication_type,
            recipient_group,
            recipient_email,
            subject,
            body,
            file_id,
            created_at
        FROM fact_communications
        WHERE status = 'Sent - Dev Simulated'
        ORDER BY created_at ASC
        """
    )

    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def fetch_package_summary(cursor, communication_id):
    cursor.execute(
        """
        SELECT TOP 1
            package_id,
            recipient_group_id,
            summary_text
        FROM fact_communication_packages
        WHERE communication_id = ?
        ORDER BY created_at DESC
        """,
        communication_id,
    )

    row = cursor.fetchone()

    if not row:
        return None

    return {
        "package_id": row[0],
        "recipient_group_id": row[1],
        "summary_text": row[2],
    }


def mark_communication_as_real_dev_sent(cursor, communication_id, provider_message_id):
    cursor.execute(
        """
        UPDATE fact_communications
        SET
            status = 'Sent - Dev Email',
            communication_status = 'Sent - Dev Email',
            sent_at = SYSUTCDATETIME(),
            last_attempt_at = SYSUTCDATETIME(),
            provider_message_id = ?,
            send_attempts = send_attempts + 1,
            error_message = NULL
        WHERE communication_id = ?
        """,
        provider_message_id,
        communication_id,
    )


def mark_communication_as_failed(cursor, communication_id, error_message):
    cursor.execute(
        """
        UPDATE fact_communications
        SET
            status = 'Failed - Dev Email',
            communication_status = 'Failed - Dev Email',
            last_attempt_at = SYSUTCDATETIME(),
            send_attempts = send_attempts + 1,
            error_message = ?
        WHERE communication_id = ?
        """,
        error_message,
        communication_id,
    )


# ============================================================
# SMTP EMAIL SENDING
# ============================================================

def generate_smtp_message_id():
    return "SMTP-DEV-" + str(uuid.uuid4())[:8]


def build_email_message(communication, attachment_path=None):
    if not DEV_EMAIL_OVERRIDE:
        raise ValueError("DEV_EMAIL_OVERRIDE is missing from .env")

    if not SMTP_FROM_EMAIL:
        raise ValueError("SMTP_FROM_EMAIL is missing from .env")

    original_subject = communication.get("subject") or communication.get("email_type")
    package_summary = communication.get("package_summary")
    original_body = communication.get("body")

    if package_summary:
        original_body = (
            f"Package ID: {package_summary['package_id']}\n"
            f"Package group: {package_summary['recipient_group_id']}\n\n"
            f"{package_summary.get('summary_text')}"
        )

    msg = EmailMessage()
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = DEV_EMAIL_OVERRIDE
    msg["Subject"] = f"[DEV TEST] {original_subject}"

    body = (
        "DEV TEST EMAIL ONLY.\n"
        "This was generated by the intern-system pipeline.\n"
        "Do not forward or use as a real HR/Coparmex communication yet.\n\n"
        "Original intended recipient:\n"
        f"{communication.get('sent_to')}\n\n"
        "Original recipient group:\n"
        f"{communication.get('recipient_group')}\n\n"
        "Original message:\n\n"
        f"{original_body}\n"
    )

    msg.set_content(body)

    if attachment_path:
        path = Path(attachment_path)

        with open(attachment_path, "rb") as file:
            file_data = file.read()

        msg.add_attachment(
            file_data,
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name,
        )

    return msg


def send_smtp_email(communication, attachment_path=None):
    if not SMTP_USERNAME:
        raise ValueError("SMTP_USERNAME is missing from .env")

    if not SMTP_PASSWORD:
        raise ValueError("SMTP_PASSWORD is missing from .env")

    msg = build_email_message(
        communication=communication,
        attachment_path=attachment_path
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    return generate_smtp_message_id()


# ============================================================
# MAIN
# ============================================================

def send_real_dev_emails_smtp():
    required_env_vars = {
        "SQL_SERVER": SQL_SERVER,
        "SQL_DATABASE": SQL_DATABASE,
        "SMTP_HOST": SMTP_HOST,
        "SMTP_PORT": SMTP_PORT,
        "SMTP_USERNAME": SMTP_USERNAME,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "SMTP_FROM_EMAIL": SMTP_FROM_EMAIL,
        "DEV_EMAIL_OVERRIDE": DEV_EMAIL_OVERRIDE,
    }

    missing = [key for key, value in required_env_vars.items() if not value]

    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        communications = fetch_dev_simulated_communications(cursor)

        if not communications:
            print("No Sent - Dev Simulated communications found.")
            print("Run scripts/send_prepared_communications.py first.")
            return

        print(f"Dev simulated communications found: {len(communications)}")

        sent_count = 0
        failed_count = 0

        for communication in communications:
            communication_id = communication["communication_id"]

            try:
                try:
                    communication["package_summary"] = fetch_package_summary(
                        cursor,
                        communication_id
                    )
                except Exception as package_error:
                    communication["package_summary"] = None
                    print("Package metadata not available; using legacy communication body.")
                    print(package_error)

                attachment_path = download_error_report_if_available(
                    communication.get("file_id")
                )

                if attachment_path:
                    print(f"Attachment found: {attachment_path}")
                else:
                    print("No attachment found for this communication.")

                provider_message_id = send_smtp_email(
                    communication=communication,
                    attachment_path=attachment_path
                )

                mark_communication_as_real_dev_sent(
                    cursor=cursor,
                    communication_id=communication_id,
                    provider_message_id=provider_message_id
                )

                sent_count += 1
                print(f"Real dev email sent: {communication_id}")

            except Exception as e:
                failed_count += 1

                mark_communication_as_failed(
                    cursor=cursor,
                    communication_id=communication_id,
                    error_message=str(e)
                )

                print(f"Failed real dev email: {communication_id}")
                print(e)

        conn.commit()

        print("\nMVP 5B completed.")
        print(f"Real dev emails sent: {sent_count}")
        print(f"Failed: {failed_count}")

    except Exception as e:
        conn.rollback()
        print("Error while sending real dev emails through SMTP:")
        print(e)
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    send_real_dev_emails_smtp()
