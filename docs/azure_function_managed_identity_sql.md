# Azure Function Managed Identity SQL Setup

Manual Azure setup required for deployed Function SQL auth.

## 1. Enable Function App Identity

In Azure Portal:

- Function App: `mex-intern-pipeline-func-win`
- Identity
- System assigned
- Status: On
- Save

## 2. Create SQL User For The Function Identity

Connect to Azure SQL database `intern_system_dev` as an Entra admin, then run:

```sql
CREATE USER [mex-intern-pipeline-func-win] FROM EXTERNAL PROVIDER;
```

If the name is already used, skip this command.

## 3. Grant MVP Permissions

For the local-first MVP, grant read/write permissions on existing pipeline tables and views:

```sql
ALTER ROLE db_datareader ADD MEMBER [mex-intern-pipeline-func-win];
ALTER ROLE db_datawriter ADD MEMBER [mex-intern-pipeline-func-win];
```

If you want the Function to run setup scripts later, also grant DDL permissions, but the preferred MVP flow is to run SQL scripts manually in Query Editor.

## 4. Function App Settings

Set:

```text
AZURE_SQL_AUTH_MODE=managed_identity
```

For local development, keep:

```text
AZURE_SQL_AUTH_MODE=interactive
```
