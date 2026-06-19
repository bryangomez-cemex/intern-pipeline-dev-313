# Power Automate Outlook To Blob

Goal: Outlook attachment lands in Azure Blob `raw-uploads`; Azure Function triggers automatically.

## Flow Shape

Trigger:

- Office 365 Outlook - When a new email arrives

Condition:

- `hasAttachments` is `true`

True branch:

- Apply to each attachment
- Get attachment
- Azure Blob Storage - Create blob

Blob target:

- Container/folder: `raw-uploads` or `raw-uploads/email_intake`
- Blob name should include `email_intake/`, for example:

```text
email_intake/@{triggerOutputs()?['body/id']}_@{items('Apply_to_each')?['name']}
```

Once the blob is created, `intern-pipeline-dev` triggers from `raw-uploads/{name}`.

## Common Error

Error:

```text
storage account in authentication does not match operation parameter
```

Fix:

- Use the same storage account in the Azure Blob Storage action as the connection.
- Or recreate the Azure Blob Storage connection using the correct storage account key.
