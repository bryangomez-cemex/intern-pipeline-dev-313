import os

import requests
from dotenv import load_dotenv


load_dotenv()


GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID")
GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID")
GRAPH_CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET")
GRAPH_SENDER_USER = os.getenv("GRAPH_SENDER_USER")
EMAIL_MODE = os.getenv("EMAIL_MODE", "simulation").strip().lower()


def is_graph_configured():
    return all([
        GRAPH_TENANT_ID,
        GRAPH_CLIENT_ID,
        GRAPH_CLIENT_SECRET,
        GRAPH_SENDER_USER,
    ])


def _get_graph_token():
    if not is_graph_configured():
        raise ValueError("Microsoft Graph email is not configured.")

    response = requests.post(
        f"https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token",
        data={
            "client_id": GRAPH_CLIENT_ID,
            "client_secret": GRAPH_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def send_graph_email(to, subject, body, attachments=None, cc=None, bcc=None):
    if EMAIL_MODE not in {"graph_draft", "graph_send"}:
        print(f"EMAIL_MODE={EMAIL_MODE}; Graph email not sent.")
        return {"status": "skipped", "mode": EMAIL_MODE}

    if EMAIL_MODE == "graph_draft":
        print("EMAIL_MODE=graph_draft; draft creation is reserved for production Graph setup.")
        return {"status": "draft_skipped", "mode": EMAIL_MODE}

    token = _get_graph_token()
    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body,
            },
            "toRecipients": [
                {"emailAddress": {"address": address}}
                for address in ([to] if isinstance(to, str) else to)
            ],
        },
        "saveToSentItems": "true",
    }

    if cc:
        message["message"]["ccRecipients"] = [
            {"emailAddress": {"address": address}}
            for address in ([cc] if isinstance(cc, str) else cc)
        ]

    if bcc:
        message["message"]["bccRecipients"] = [
            {"emailAddress": {"address": address}}
            for address in ([bcc] if isinstance(bcc, str) else bcc)
        ]

    if attachments:
        raise NotImplementedError("Graph attachment upload is intentionally deferred for the safe MVP.")

    response = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{GRAPH_SENDER_USER}/sendMail",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=message,
        timeout=30,
    )
    response.raise_for_status()
    return {"status": "sent", "mode": EMAIL_MODE}


def download_graph_message_attachments(message_id):
    if EMAIL_MODE not in {"graph_draft", "graph_send"}:
        print(f"EMAIL_MODE={EMAIL_MODE}; Graph attachment download not enabled.")
        return []

    token = _get_graph_token()
    response = requests.get(
        f"https://graph.microsoft.com/v1.0/users/{GRAPH_SENDER_USER}/messages/{message_id}/attachments",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("value", [])
