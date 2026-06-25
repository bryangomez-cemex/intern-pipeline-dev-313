"""
Centralized email service — Azure Communication Services (ACS) Email.

No Microsoft Graph, no SMTP. Config is read only from environment variables.

IMPORTANT: these vars must also be set in the Azure Function App:
  Portal → Function App → Settings → Environment variables / Configuration →
  Application settings.

  EMAIL_PROVIDER=azure_communication_services
  EMAIL_SIMULATION_MODE=true            # safe default; set false to send for real
  ACS_CONNECTION_STRING=<acs connection string>
  ACS_SENDER_EMAIL=<verified sender, e.g. donotreply@<domain>>
  ACS_SENDER_NAME=Intern Pipeline
"""

import os

try:
    from dotenv import load_dotenv  # optional, for local testing
    load_dotenv()
except Exception:
    pass

PROVIDER = "azure_communication_services"


def _simulation_mode():
    return os.getenv("EMAIL_SIMULATION_MODE", "true").strip().lower() == "true"


def send_email(to_email, subject, html_body, to_name=None, cc=None,
               attachments=None, metadata=None):
    """Send an email via Azure Communication Services.

    Returns a dict: {"status": "sent"|"failed"|"simulated", "provider": ..., ...}
    """
    # Validation — works the same in simulation and real mode.
    if not to_email or not subject or not html_body:
        return {"status": "failed", "provider": PROVIDER,
                "error": "to_email, subject and html_body are required"}

    # Simulation mode: never send; just log. No ACS credentials required.
    if _simulation_mode():
        preview = " ".join(str(html_body).split())[:200]
        cc_str = (" cc=" + ",".join(cc)) if cc else ""
        print(f"[EMAIL SIMULATED] provider={PROVIDER} to={to_email}{cc_str} subject={subject!r}")
        print(f"  html preview: {preview!r}")
        return {"status": "simulated", "provider": PROVIDER}

    conn = os.getenv("ACS_CONNECTION_STRING")
    sender = os.getenv("ACS_SENDER_EMAIL")
    if not conn or not sender:
        return {"status": "failed", "provider": PROVIDER,
                "error": "ACS_CONNECTION_STRING and ACS_SENDER_EMAIL are required when EMAIL_SIMULATION_MODE=false"}

    try:
        from azure.communication.email import EmailClient

        client = EmailClient.from_connection_string(conn)
        message = {
            "senderAddress": sender,
            "content": {"subject": subject, "html": html_body},
            "recipients": {"to": [{"address": to_email, "displayName": to_name or ""}]},
        }
        if cc:
            message["recipients"]["cc"] = [{"address": a} for a in cc if a]
        # TODO: ACS attachment support is not implemented yet. Attachments are
        # accepted (and preserved upstream) but not yet sent via ACS — wire this
        # using message["attachments"] with base64 content when needed.
        poller = client.begin_send(message)
        result = poller.result()
        message_id = None
        try:
            message_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        except Exception:
            pass
        return {"status": "sent", "provider": PROVIDER, "id": message_id}
    except Exception as e:
        return {"status": "failed", "provider": PROVIDER, "error": str(e)}
