# Email Setup & Go-Live Guide

The pipeline is wired for real email via **Microsoft Graph (Office 365)**, but real
sending is **OFF** until you complete the steps below. Until then, every
communication is recorded in `fact_communications` and visible in Power BI, but
nothing leaves the system.

## How it works (two stages)

1. **Prepare** (automatic): when a file is processed, the pipeline writes a row
   into `fact_communications` (status `Prepared`) with recipient, subject, body.
   No email is sent here.
2. **Send** (manual/scheduled): `scripts/send_prepared_communications.py` reads
   `Prepared` rows and delivers them. It only sends for real when
   `SEND_EMAILS=true` **and** `EMAIL_MODE=graph_send` **and** Graph is configured.
   Otherwise it simulates and marks rows `Sent - Dev Simulated`.

## 1. Set the recipient addresses (no code change)

Recipients for fixed groups now come from the `dim_email_recipients` table.
Replace the demo addresses with the real ones:

```sql
UPDATE dim_email_recipients SET email = 'rh.practicantes@cemex.com' WHERE recipient_id = 'ER001';
UPDATE dim_email_recipients SET email = 'hr.ops@cemex.com'          WHERE recipient_id = 'ER002';
UPDATE dim_email_recipients SET email = 'contacto@coparmex.org.mx'  WHERE recipient_id = 'ER003';
-- add more rows per group as needed; active_flag = 1 means "in use".
```

- **HR** communications go to every active `recipient_group = 'HR'` row (joined).
- **Coparmex** communications go to active `recipient_group = 'Coparmex'` rows.
- **Applicant** messages use the intern's own email if present in the data,
  otherwise the single inbox in `DEV_EMAIL_OVERRIDE` (set this to an HR intake
  mailbox). Per-applicant routing for batch files is a future enhancement.

## 2. Provide Microsoft Graph credentials

Create (or have CEMEX IT create) an **Entra app registration** with the
**`Mail.Send`** application permission (admin-consented), then set these as app
settings on the Function App **and** in your local `.env`:

| Setting | Value |
|---|---|
| `GRAPH_TENANT_ID` | CEMEX Entra tenant id |
| `GRAPH_CLIENT_ID` | app registration client id |
| `GRAPH_CLIENT_SECRET` | app registration client secret |
| `GRAPH_SENDER_USER` | the mailbox to send from, e.g. `intern-pipeline@cemex.com` |

Set them on the Function App with:

```bash
az functionapp config appsettings set \
  --name mex-intern-pipeline-func-win --resource-group rg-intern-system-dev \
  --settings GRAPH_TENANT_ID=... GRAPH_CLIENT_ID=... GRAPH_CLIENT_SECRET=... GRAPH_SENDER_USER=intern-pipeline@cemex.com
```

## 3. Flip the switch (when ready)

```bash
# local .env or Function App app settings
SEND_EMAILS=true
EMAIL_MODE=graph_send   # graph_draft = build but don't send; simulation = safe default
```

Then run the sender:

```bash
EMAIL_MODE=graph_send SEND_EMAILS=true .venv/bin/python scripts/send_prepared_communications.py
```

Start with **one** recipient (override `dim_email_recipients` to your own inbox)
to confirm delivery before pointing at the real HR/Coparmex addresses.

## What I need from you to finish

- The 4 Graph values in the table above (or have CEMEX IT create the app registration).
- The real HR and Coparmex email addresses (I can run the `UPDATE` statements).
