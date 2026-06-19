# intern-pipeline-dev Azure Function

Deploy this folder to the existing Azure Function App:

- Function App: `intern-pipeline-dev`
- Resource group: `rg-intern-system-dev`
- Runtime: Python
- Hosting: Flex Consumption
- OS: Linux
- Trigger container: `raw-uploads`

The Blob Trigger listens on:

```text
raw-uploads/{name}
```

It calls:

```python
process_blob_by_name("raw-uploads", name, run_type="blob_trigger")
```

## Before Deploying

From the repo root:

```bash
python scripts/sync_function_modules.py
python scripts/check_function_readiness.py
```

The Function folder includes a synced copy of the required pipeline modules in `azure_function_app/scripts/` so deployment of this folder works by itself.

## VS Code Deployment

1. Open the `azure_function_app/` folder in VS Code.
2. Sign into Azure.
3. Use the Azure Functions extension.
4. Deploy to existing Function App: `intern-pipeline-dev`.

## Azure CLI Deployment

If Azure Functions Core Tools and Azure CLI are installed:

```bash
az login
az account set --subscription "<subscription-name-or-id>"
cd azure_function_app
func azure functionapp publish intern-pipeline-dev --python
```

## Required App Settings

Add these in Azure Portal for `intern-pipeline-dev`:

```text
AZURE_STORAGE_CONNECTION_STRING=<storage connection string>
RAW_UPLOADS_CONTAINER=raw-uploads
ERROR_REPORTS_CONTAINER=error-reports
ARCHIVE_CONTAINER=archive
AZURE_SQL_SERVER=<server>.database.windows.net
AZURE_SQL_DATABASE=intern_system_dev
AZURE_SQL_AUTH_MODE=managed_identity
EMAIL_MODE=simulation
DEV_EMAIL_OVERRIDE=<dev-only inbox>
```

For first Azure testing, keep:

```text
EMAIL_MODE=simulation
```

Use:

```text
AZURE_SQL_AUTH_MODE=managed_identity
```

only after the Function App managed identity has SQL permissions.

Do not configure real HR, Coparmex, or applicant recipients yet.
