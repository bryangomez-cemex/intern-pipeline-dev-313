import argparse
import csv
import io
import os
import smtplib
from datetime import datetime, UTC
from email.message import EmailMessage

from dotenv import load_dotenv

import azure_clients


load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USERNAME
DEFAULT_RECIPIENT = os.getenv("REPORT_RECIPIENT_EMAIL") or os.getenv("DEV_EMAIL_OVERRIDE") or SMTP_USERNAME


REPORT_QUERY = """
SELECT
    intern_id,
    employee_number,
    intern_name,
    position_name,
    manager,
    vp,
    ubicacion_hc,
    estado_ubicacion_hc,
    cia_hc,
    oi_hc,
    cc_hc,
    start_date,
    contract_end_date,
    days_until_contract_end,
    raw_status,
    alert_label
FROM dbo.vw_powerbi_expired_active_contracts
ORDER BY contract_end_date, vp, intern_name;
"""


def fetch_expired_active_contracts():
    conn = azure_clients.get_sql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(REPORT_QUERY)
        columns = [column[0] for column in cursor.description]
        return columns, [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close()


def build_csv(columns, rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column) for column in columns})
    return output.getvalue()


def build_body(rows):
    today = datetime.now(UTC).date().isoformat()
    lines = [
        f"Reporte generado el {today}.",
        "",
        f"Practicantes activos con contrato vencido: {len(rows)}",
        "",
    ]

    if rows:
        lines.extend([
            "Resumen:",
            "",
        ])
        for row in rows:
            lines.append(
                "- {intern_name} | Num: {employee_number} | VP: {vp} | Jefe: {manager} | Fecha fin: {contract_end_date}".format(
                    intern_name=row.get("intern_name") or "",
                    employee_number=row.get("employee_number") or "",
                    vp=row.get("vp") or "",
                    manager=row.get("manager") or "",
                    contract_end_date=row.get("contract_end_date") or "",
                )
            )
        lines.extend([
            "",
            "Se adjunta CSV con el detalle completo.",
        ])
    else:
        lines.append("No hay practicantes activos con contrato vencido.")

    return "\n".join(lines)


def send_email(recipient, subject, body, csv_content, attachment_name, dry_run=False):
    if dry_run:
        print("DRY RUN - email not sent")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(body)
        print(f"Attachment: {attachment_name} ({len(csv_content)} bytes)")
        return "dry-run"

    if not recipient:
        raise ValueError("No recipient configured. Set REPORT_RECIPIENT_EMAIL or DEV_EMAIL_OVERRIDE.")

    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise ValueError("SMTP_USERNAME / SMTP_PASSWORD missing from environment.")

    message = EmailMessage()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        csv_content.encode("utf-8"),
        maintype="text",
        subtype="csv",
        filename=attachment_name,
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)

    return "sent"


def main():
    parser = argparse.ArgumentParser(description="Email active interns with expired contracts.")
    parser.add_argument("--to", default=DEFAULT_RECIPIENT, help="Recipient email. Defaults to REPORT_RECIPIENT_EMAIL or DEV_EMAIL_OVERRIDE.")
    parser.add_argument("--send", action="store_true", help="Actually send the email. Without this flag, prints a dry run.")
    args = parser.parse_args()

    columns, rows = fetch_expired_active_contracts()
    today = datetime.now(UTC).date().isoformat()
    csv_content = build_csv(columns, rows)
    subject = f"Practicantes activos con contrato vencido - {today}"
    body = build_body(rows)
    attachment_name = f"practicantes_activos_contrato_vencido_{today}.csv"

    result = send_email(
        recipient=args.to,
        subject=subject,
        body=body,
        csv_content=csv_content,
        attachment_name=attachment_name,
        dry_run=not args.send,
    )
    print(f"expired_active_count={len(rows)}")
    print(f"email_status={result}")
    print(f"recipient={args.to}")


if __name__ == "__main__":
    main()
