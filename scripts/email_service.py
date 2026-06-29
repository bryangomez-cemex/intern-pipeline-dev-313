"""Centralized email service using Gmail SMTP.

Config is read only from environment variables.

Required in Azure Function App settings:
  EMAIL_PROVIDER=smtp
  EMAIL_SIMULATION_MODE=true|false
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USERNAME=<gmail address>
  SMTP_PASSWORD=<gmail app password>
  SMTP_FROM_EMAIL=<gmail address>
  SMTP_FROM_NAME=Programa de Practicantes CEMEX
"""

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

try:
    from dotenv import load_dotenv  # optional, for local testing
    load_dotenv()
except Exception:
    pass

PROVIDER = "smtp"


def _build_attachments(attachments):
    """Normalize attachment inputs into (name, content_type, bytes) tuples.

    Accepts local file paths or (name, bytes) tuples. Unreadable items are
    skipped with a log note instead of failing the whole email.
    """
    built = []
    for item in attachments or []:
        try:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                name, raw = item
                data = bytes(raw) if isinstance(raw, (bytes, bytearray)) else open(raw, "rb").read()
            else:
                name = os.path.basename(str(item))
                with open(item, "rb") as fh:
                    data = fh.read()
            ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
            built.append((name, ctype, data))
        except Exception as exc:
            print(f"[EMAIL] attachment skipped ({item!r}): {exc}")
    return built


def _simulation_mode():
    return os.getenv("EMAIL_SIMULATION_MODE", "true").strip().lower() == "true"


def send_email(to_email, subject, html_body, to_name=None, cc=None,
               attachments=None, metadata=None):
    """Send an email via Gmail SMTP.

    Returns a dict: {"status": "sent"|"failed"|"simulated", "provider": ..., ...}
    """
    # Validation — works the same in simulation and real mode.
    if not to_email or not subject or not html_body:
        return {"status": "failed", "provider": PROVIDER,
                "error": "to_email, subject and html_body are required"}

    # Simulation mode: never send; just log. No SMTP credentials required.
    if _simulation_mode():
        preview = " ".join(str(html_body).split())[:200]
        cc_str = (" cc=" + ",".join(cc)) if cc else ""
        att = _build_attachments(attachments)
        att_str = (" attachments=" + ",".join(a[0] for a in att)) if att else ""
        print(f"[EMAIL SIMULATED] provider={PROVIDER} to={to_email}{cc_str}{att_str} subject={subject!r}")
        print(f"  html preview: {preview!r}")
        return {"status": "simulated", "provider": PROVIDER, "attachments": len(att)}

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM_EMAIL") or smtp_username
    sender_name = os.getenv("SMTP_FROM_NAME", "Programa de Practicantes CEMEX")

    if not smtp_username or not smtp_password or not sender:
        return {"status": "failed", "provider": PROVIDER,
                "error": "SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM_EMAIL are required when EMAIL_SIMULATION_MODE=false"}

    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((sender_name, sender))
        message["To"] = formataddr((to_name or "", to_email))
        if cc:
            message["Cc"] = ", ".join(a for a in cc if a)

        text_fallback = " ".join(str(html_body).replace("<br>", "\n").split())
        message.set_content(text_fallback)
        message.add_alternative(html_body, subtype="html")

        built_attachments = _build_attachments(attachments)
        for name, ctype, data in built_attachments:
            maintype, _, subtype = ctype.partition("/")
            message.add_attachment(
                data,
                maintype=maintype or "application",
                subtype=subtype or "octet-stream",
                filename=name,
            )

        recipients = [to_email] + [a for a in (cc or []) if a]
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(message, from_addr=sender, to_addrs=recipients)

        return {"status": "sent", "provider": PROVIDER,
                "attachments": len(built_attachments)}
    except Exception as e:
        return {"status": "failed", "provider": PROVIDER, "error": str(e)}
