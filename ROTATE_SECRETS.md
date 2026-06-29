# Secret Rotation Checklist

## 0. CI Service Principal password — ROTATED (done 2026-06-22)

The `intern-pipeline-ci` Service Principal (appId `7f2c34ab-3b7f-4089-aee1-da0052ee1814`)
password appeared in plaintext in a working session, so it was reset with
`az ad sp credential reset` and the new value was written straight into the
`AZURE_SQL_CONNECTION_STRING` GitHub secret. CI was re-run and passed with the
rotated credential. No further action needed unless it is exposed again.

## 1. Azure SQL password (`bryan-admin`)

NOTE: the SQL server `rg-intern-system-dev` enforces **Microsoft Entra-only
authentication**, so this SQL login/password cannot actually be used to connect.
Rotating it is good hygiene but is not security-critical for the pipeline.

- [ ] Sign in to the Azure Portal
- [ ] Navigate to **SQL Server** `rg-intern-system-dev` → Security → SQL Authentication
- [ ] Reset the password for login `bryan-admin`
- [ ] Update any local `.env` if the password is stored there

## 2. Azure App Service publish profile (Kudu)

- [ ] Navigate to **App Service** `mex-intern-pipeline-func-win` (or the relevant Function App)
- [ ] Under **Overview** → click **Get publish profile** → then **Reset publish profile**
- [ ] Download the new publish profile and update any deployment credentials or GitHub secrets that use it (e.g. `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`)

## 3. Gmail app password (`reddetalentocemex@gmail.com`)

The Gmail app password was shared in a working session to configure the live
pipeline. It should be rotated after the Azure Function App Gmail IMAP/SMTP
configuration is confirmed working.

- [ ] Create a new Google app password for `reddetalentocemex@gmail.com`
- [ ] Update Azure Function App settings `IMAP_PASSWORD` and `SMTP_PASSWORD`
- [ ] Restart Function App `mex-intern-pipeline-func-win`
- [ ] Send a test email with an allowed attachment to confirm intake still works
- [ ] Confirm outbound SMTP sends from the Gmail account

## After rotation

- Verify the pipeline can still connect to Azure SQL (Gate 1 test)
- Verify any CI/CD workflows that use the publish profile still deploy successfully
