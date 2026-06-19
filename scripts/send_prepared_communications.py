import os
import struct
import uuid
from datetime import datetime, UTC

import pyodbc
from dotenv import load_dotenv
from azure.identity import InteractiveBrowserCredential


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")


# ============================================================
# SQL CONNECTION USING MICROSOFT ENTRA TOKEN
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
# DEV EMAIL SIMULATION
# ============================================================

def generate_dev_message_id():
    return "DEV-MSG-" + str(uuid.uuid4())[:8]


def fetch_prepared_communications(cursor):
    cursor.execute(
        """
        SELECT TOP 20
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
        WHERE status = 'Prepared'
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


def mark_communication_as_sent_simulated(cursor, communication_id, provider_message_id):
    cursor.execute(
        """
        UPDATE fact_communications
        SET
            status = 'Sent - Dev Simulated',
            communication_status = 'Sent - Dev Simulated',
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
            status = 'Failed',
            communication_status = 'Failed',
            last_attempt_at = SYSUTCDATETIME(),
            send_attempts = send_attempts + 1,
            error_message = ?
        WHERE communication_id = ?
        """,
        error_message,
        communication_id,
    )


def simulate_send_email(communication):
    """
    Safe MVP 5A behavior:
    This does NOT send a real email.
    It only prints what would be sent and returns a fake provider message id.
    """
    print("\n========================================")
    print("DEV EMAIL SIMULATION")
    print("========================================")
    print(f"Communication ID: {communication['communication_id']}")
    print(f"Email Type: {communication['email_type']}")
    print(f"Recipient Group: {communication.get('recipient_group')}")
    print(f"To: {communication['sent_to']}")
    print(f"Subject: {communication.get('subject')}")
    print("----------------------------------------")
    if communication.get("package_summary"):
        print(f"Package ID: {communication['package_summary']['package_id']}")
        print(f"Package Group: {communication['package_summary']['recipient_group_id']}")
        print(communication["package_summary"].get("summary_text"))
    else:
        print(communication.get("body"))
    print("========================================\n")

    return generate_dev_message_id()


def send_prepared_communications():
    if not SQL_SERVER:
        raise ValueError("AZURE_SQL_SERVER is missing from .env")

    if not SQL_DATABASE:
        raise ValueError("AZURE_SQL_DATABASE is missing from .env")

    conn = get_sql_connection()
    cursor = conn.cursor()

    try:
        communications = fetch_prepared_communications(cursor)

        if not communications:
            print("No prepared communications found.")
            return

        print(f"Prepared communications found: {len(communications)}")

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

                provider_message_id = simulate_send_email(communication)

                mark_communication_as_sent_simulated(
                    cursor=cursor,
                    communication_id=communication_id,
                    provider_message_id=provider_message_id
                )

                sent_count += 1
                print(f"Marked as sent simulation: {communication_id}")

            except Exception as e:
                failed_count += 1

                mark_communication_as_failed(
                    cursor=cursor,
                    communication_id=communication_id,
                    error_message=str(e)
                )

                print(f"Failed communication: {communication_id}")
                print(e)

        conn.commit()

        print("\nMVP 5A completed.")
        print(f"Sent simulations: {sent_count}")
        print(f"Failed: {failed_count}")

    except Exception as e:
        conn.rollback()
        print("Error while sending prepared communications:")
        print(e)
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    send_prepared_communications()
