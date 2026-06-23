import os
import sys
import uuid

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import azure_clients
import graph_email_client


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

SQL_SERVER = os.getenv("AZURE_SQL_SERVER")
SQL_DATABASE = os.getenv("AZURE_SQL_DATABASE")

# Real send is OFF unless BOTH are set: SEND_EMAILS=true and a Graph mode.
SEND_EMAILS = os.getenv("SEND_EMAILS", "false").strip().lower() == "true"
EMAIL_MODE = os.getenv("EMAIL_MODE", "simulation").strip().lower()


# ============================================================
# SQL CONNECTION (shared auth: managed identity / token / connection string)
# ============================================================

def get_sql_connection():
    return azure_clients.get_sql_connection()


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


def mark_communication_as_sent(cursor, communication_id, provider_message_id, status_label):
    cursor.execute(
        """
        UPDATE fact_communications
        SET
            status = ?,
            communication_status = ?,
            sent_at = SYSUTCDATETIME(),
            last_attempt_at = SYSUTCDATETIME(),
            provider_message_id = ?,
            send_attempts = send_attempts + 1,
            error_message = NULL
        WHERE communication_id = ?
        """,
        status_label,
        status_label,
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


def build_recipient_list(communication):
    raw = communication.get("recipient_email") or communication.get("sent_to") or ""
    return [address.strip() for address in str(raw).split(";") if address.strip()]


def deliver_communication(communication):
    """
    Dispatch a prepared communication.

    Real email is only sent when SEND_EMAILS=true AND EMAIL_MODE=graph_send AND
    Microsoft Graph is fully configured. In every other case this safely simulates
    and records the row as 'Sent - Dev Simulated' — nothing leaves the system.
    Returns (provider_message_id, status_label).
    """
    recipients = build_recipient_list(communication)

    subject = communication.get("subject") or ""
    body = communication.get("body") or ""
    if communication.get("package_summary"):
        body = communication["package_summary"].get("summary_text") or body

    if SEND_EMAILS and EMAIL_MODE in {"graph_send", "graph_draft"} and graph_email_client.is_graph_configured():
        if not recipients:
            raise ValueError("Communication has no recipient email address.")

        result = graph_email_client.send_graph_email(to=recipients, subject=subject, body=body)

        if result.get("status") == "sent":
            print(f"Graph email sent to {recipients}")
            return "GRAPH-" + str(uuid.uuid4())[:8], "Sent"

        # Graph self-gated (e.g. mode=graph_draft) — do not claim a real send.
        print(f"Graph send not performed (mode={result.get('mode')}); recording as simulated.")
        return generate_dev_message_id(), "Sent - Dev Simulated"

    simulate_send_email(communication)
    return generate_dev_message_id(), "Sent - Dev Simulated"


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

                provider_message_id, status_label = deliver_communication(communication)

                mark_communication_as_sent(
                    cursor=cursor,
                    communication_id=communication_id,
                    provider_message_id=provider_message_id,
                    status_label=status_label,
                )

                sent_count += 1
                print(f"Marked as {status_label}: {communication_id}")

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
