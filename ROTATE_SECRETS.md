# Secret Rotation Checklist

Two secrets were exposed in a prior conversation. Complete both steps before the next demo.

## 1. Azure SQL password (`bryan-admin`)

- [ ] Sign in to the Azure Portal
- [ ] Navigate to **SQL Server** `rg-intern-system-dev` → Security → SQL Authentication
- [ ] Reset the password for login `bryan-admin`
- [ ] Update `AZURE_SQL_PASSWORD` in GitHub Actions secrets with the new password
- [ ] Update any local `.env` if the password is stored there

## 2. Azure App Service publish profile (Kudu)

- [ ] Navigate to **App Service** `mex-intern-pipeline-func-win` (or the relevant Function App)
- [ ] Under **Overview** → click **Get publish profile** → then **Reset publish profile**
- [ ] Download the new publish profile and update any deployment credentials or GitHub secrets that use it (e.g. `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`)

## After rotation

- Verify the pipeline can still connect to Azure SQL (Gate 1 test)
- Verify any CI/CD workflows that use the publish profile still deploy successfully
