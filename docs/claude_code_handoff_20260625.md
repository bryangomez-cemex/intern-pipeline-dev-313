# Claude Code Handoff - Intern System Pipeline

Date: 2026-06-25  
Repo: `/Users/bryangomezcemex/intern-system-pipeline`  
Branch: `codex/intern-pipeline-production-readiness`  
Latest local commit before this handoff: `eeef3c8 Add fresh Azure SQL setup support`

## Current Status

The intern/practicante automation pipeline has been upgraded and configured for
the new Azure account/resources. Azure SQL has been initialized successfully, the
Azure Function App has been deployed, and safety settings are currently enabled
for simulation-only email behavior.

Do not deploy again unless Bryan explicitly asks for it.

## Azure Resources In Use

- Subscription name: `Azure subscription 1`
- Subscription ID: `a3d54e37-bfef-4efb-8f09-f6d848b499c7`
- Tenant ID: `6ee19001-d0c4-45f8-af8b-ff00f16d07e1`
- Resource group: `rg-intern-pipeline-dev`
- Function App: `mex-intern-pipeline-func-win`
- Function host: `mex-intern-pipeline-func-win-axgkagdsdgfbebc6.centralus-01.azurewebsites.net`
- Azure SQL server: `rg-intern-system-devbge.database.windows.net`
- Azure SQL database: `rg-intern-system-dev`
- Storage account: `rginternpipelinedevb961`
- Blob containers:
  - `raw-uploads`
  - `error-reports`
  - `archive`
- Azure Document Intelligence: `docintel-intern-pipeline-dev`
- Document Intelligence endpoint exists in Function App settings.
- Document Intelligence key exists in Function App settings.

Never print, commit, or expose connection strings, storage keys, SQL passwords,
Document Intelligence keys, SMTP secrets, or Graph secrets.

## Confirmed App Settings / Safety State

Confirmed after final deploy:

- `EMAIL_MODE=simulation`
- `SEND_EMAILS=false`
- `ENABLE_ADMIN_SQL_SETUP=false`

`AZURE_SQL_CONNECTION_STRING` exists and was corrected. It originally had
`erver=` instead of `Server=` and lacked a local-compatible ODBC driver. It was
reconstructed with `Driver={ODBC Driver 18 for SQL Server}` and the proper SQL
server/database/user/password values without printing the secret.

## What Was Done

### General System Review

- Reviewed the full system architecture:
  - Email/file intake into Blob Storage.
  - Azure Function blob trigger.
  - Python pipeline classification and processing.
  - Azure SQL operational tables.
  - Azure SQL reporting views for Power BI.
- Identified that several actions depend on Azure connections/settings:
  - SQL connection string.
  - Blob storage connection string.
  - Document Intelligence endpoint/key.
  - Function app settings.
  - Email provider settings.
- Confirmed Power Automate is no longer part of the operating path.

### Current Intern Database / Excel Processing

- Processed the up-to-date intern spreadsheet sent by Bryan.
- The spreadsheet had 3 sheets.
- The current master intern load produced:
  - 302 interns total.
  - 281 active.
  - 21 inactive.
- Cleaned stale missing-document records from previous test data in the old
  environment.
- Remaining exceptions were contract-risk style warnings, not missing package
  requirements.

### Package 1 Requirements

Updated Package 1 to Spanish/business naming:

- `Paquete 1`
- Professional photo no longer required.
- Required:
  - Alta
  - CURP
  - Constancia de estudios
  - Identificacion
  - Comprobante de domicilio
- Emergency contact is expected to be captured from email/body text when
  available.

### Azure Document Intelligence

- Confirmed Document Intelligence settings exist in the Function App.
- The system can use Document Intelligence for scanned PDFs/images when
  configured.
- For text-layer PDFs, local parsing with `pypdf` remains available.

### Matching / CEMEX HR Relationship Logic

Implemented/defined relationship matching logic for:

- `CIA HC`
- `VP HC`
- `CC HC`
- `OI HC`
- `JefeInmediato`

Hierarchy:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

Strong matching signals:

- `JefeInmediato -> VP HC`
- `JefeInmediato -> CC HC`
- `JefeInmediato -> OI HC`
- `JefeInmediato -> CIA HC`
- `OI HC -> VP HC`
- `OI HC -> CC HC`
- `CC HC -> VP HC`
- `CC HC -> CIA HC`

If one of those fields is empty, the system should infer/fill the value using
the strongest available relation for that row. Matching uses historical
`dim_interns` data and `dim_manager_assignments` where available.

### Sequential ID / Concurrency Safety

- Implemented safer sequential ID generation using SQL application locks around
  prefix-based ID generation.
- This reduces collision risk when multiple blob triggers run in parallel.

### Baja Automation

Implemented baja transition logic:

- Detects when an intern changes from active/activo/ST002 to inactive/baja.
- Removes the intern from active status views because status changes are
  reflected in `dim_interns` / lifecycle events.
- Creates a lifecycle event for baja.
- Prepares an HR communication with subject:

```text
Baja De Practicante - [NOMBRE DE PRACTICANTE]
```

The email body includes:

- Fecha de nacimiento
- Correo personal
- Universidad
- Carrera
- Semestre
- Fecha de graduacion
- CEMEX-ID
- Correo institucional CEMEX
- Vicepresidencia
- Nombre del proyecto
- Jefe directo
- AIRH
- Ubicacion UDN
- Compania
- OI
- CC
- Sueldo
- Fecha de ingreso
- Fecha fin
- Estado de practicante
- Nombre completo

Email sending remains simulation-only unless Bryan explicitly enables real
Graph/SMTP settings.

### Expired Active Contracts Email Script

Added a script to generate/send a report of active interns with expired
contracts:

```text
scripts/send_expired_active_contracts_email.py
```

Important: sending real PII by email must remain disabled until Bryan explicitly
approves the recipient/provider and corporate policy route.

### Power BI

Bryan completed Power BI pages. Guidance was given for 5 no-DAX pages with SQL
views doing the calculations. Views available/verified include:

- `vw_powerbi_dashboard_kpis`
- `vw_powerbi_vp_summary`
- `vw_powerbi_location_summary`
- `vw_powerbi_contract_risk`
- `vw_powerbi_document_status`
- `vw_powerbi_document_summary`
- `vw_powerbi_hr_action_queue`
- `vw_powerbi_vacantes`
- `vw_powerbi_costos_practicantes`
- `vw_powerbi_vp_capacity`
- `vw_powerbi_expired_active_contracts`
- `vw_powerbi_inactive_interns`
- `vw_powerbi_interns_status`

VP capacity limits used:

```text
CONCRETO Y CONSTRUCCION                                  130
CADENA DE SUMINISTRO                                     127
OPERACIONES-TECNICA                                       86
SEGMENTO DISTRIBUCION                                     51
GLOBAL ENTERPRISE SERVICES                                50
RECURSOS HUMANOS                                          25
SEGMENTO INDUSTRIAL                                       23
SEGURIDAD INDUSTRIAL Y BIENESTAR                          16
ASUNTOS CORPORATIVOS, SOSTENIBILIDAD Y COMUNICACION       13
LEGAL                                                      6
PLANEACION                                                 3
SUPPLY CHAIN                                               2
CEMENT OPERATIONS                                          1
PLANNING                                                   1
PRESIDENCIA MEXICO                                         1
```

### Schema Simplification

- Added canonical views and schema simplification notes so Power BI can read
  from stable reporting views instead of raw operational tables.
- Legacy operational tables are still retained for audit, compatibility, and
  pipeline writes.

### Fresh Azure Account Setup

New Azure resources were configured after Bryan switched accounts/subscription.

Actions completed:

- Confirmed new account/subscription.
- Confirmed resources in `rg-intern-pipeline-dev`.
- Created/confirmed Blob containers:
  - `raw-uploads`
  - `error-reports`
  - `archive`
- Set safe email settings:
  - `EMAIL_MODE=simulation`
  - `SEND_EMAILS=false`
  - `EMAIL_PROVIDER=simulation`
- Corrected `AZURE_SQL_CONNECTION_STRING`.
- Synced Function modules.
- Deployed Function App ZIP successfully.
- Restarted Function App.
- Confirmed Function App running.

### Fresh Azure SQL Setup

The original SQL scripts assumed several legacy/base tables already existed.
For a brand-new database, that failed. Added base setup scripts:

- `scripts/sql/00_create_core_legacy_tables.sql`
- `scripts/sql/00_create_dim_interns.sql`

These create base compatibility tables needed by views and pipeline writes:

- `dim_interns`
- `fact_files`
- `fact_validations`
- `fact_communications`
- `dim_validation_rules`

Correct fresh database SQL order:

```text
scripts/sql/00_create_core_legacy_tables.sql
scripts/sql/00_create_dim_interns.sql
scripts/sql/create_full_mvp_pipeline.sql
scripts/sql/fix_file_id_source_file_id_compatibility.sql
scripts/sql/seed_pipeline_validation_rules.sql
scripts/sql/2026-06_package1_document_requirements.sql
scripts/sql/2026-06_resolve_stale_missing_items.sql
scripts/sql/add_corporate_column_aliases.sql
scripts/sql/create_matching_engine_v1.sql
scripts/sql/create_business_powerbi_views.sql
scripts/sql/2026-06_onboarding_schema.sql
scripts/sql/2026-06_schema_simplification.sql
scripts/sql/2026-06_powerbi_no_dax_views.sql
```

Because the local environment could not connect directly to Azure SQL due
network/firewall constraints, setup was run inside Azure using a temporary Azure
Container Instance with `mcr.microsoft.com/mssql-tools`.

Temporary resources used and cleaned:

- ACI setup container: deleted.
- ACI verification container: deleted.
- Temporary Azure Files shares `sqlsetup*`: deleted.

Verification result:

- `dbo_tables = 30`
- `dbo_views = 41`
- Missing required Power BI views: none.

### Function App Admin SQL Setup Helper

Added a guarded admin setup path in `azure_function_app/function_app.py`:

- HTTP route: `admin/setup-database`
- Startup timer: `setup_database_on_startup`
- Both are guarded by:

```text
ENABLE_ADMIN_SQL_SETUP=true
```

Current setting is:

```text
ENABLE_ADMIN_SQL_SETUP=false
```

Do not enable this unless intentionally rerunning setup/migrations.

### Git Commits Created

Important commits on `codex/intern-pipeline-production-readiness`:

- `d84ca23 Implement intern pipeline production readiness`
- `e9f003b Add baja transition communications`
- `eeef3c8 Add fresh Azure SQL setup support`

## Important Files Changed / Added

Core pipeline:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`
- `scripts/matching_engine.py`
- `scripts/lifecycle_requirements.py`
- `scripts/document_pipeline.py`
- `scripts/onboarding_pipeline.py`

Azure Function:

- `azure_function_app/function_app.py`
- `scripts/sync_function_modules.py`

SQL:

- `scripts/sql/00_create_core_legacy_tables.sql`
- `scripts/sql/00_create_dim_interns.sql`
- `scripts/sql/create_full_mvp_pipeline.sql`
- `scripts/sql/fix_file_id_source_file_id_compatibility.sql`
- `scripts/sql/seed_pipeline_validation_rules.sql`
- `scripts/sql/2026-06_package1_document_requirements.sql`
- `scripts/sql/2026-06_resolve_stale_missing_items.sql`
- `scripts/sql/add_corporate_column_aliases.sql`
- `scripts/sql/create_matching_engine_v1.sql`
- `scripts/sql/create_business_powerbi_views.sql`
- `scripts/sql/2026-06_onboarding_schema.sql`
- `scripts/sql/2026-06_schema_simplification.sql`
- `scripts/sql/2026-06_powerbi_no_dax_views.sql`

Operational scripts:

- `scripts/send_expired_active_contracts_email.py`
- `scripts/run_azure_sql_setup_container.py`
- `scripts/run_azure_sql_verify_container.py`

Docs:

- `docs/technical_manual.md`
- `docs/full_automation_deployment_guide.md`
- `docs/power_bi_no_dax_5_pages.md`
- `docs/email_alert_recommendations.md`
- `docs/schema_simplification.md`
- `docs/claude_code_handoff_20260625.md`

## What Is Not Yet Done / Next Steps

Do not deploy unless Bryan asks.

Recommended next checks:

1. Push/PR the branch if Bryan wants GitHub updated.
2. Run a real but fake-data email/blob test in Azure:
   - Upload fake current intern Excel to `raw-uploads`.
   - Confirm `fact_pipeline_runs`.
   - Confirm Power BI views update.
3. Test one requisition document and one candidate document package with fake
   data.
4. After real-life testing, decide whether to enable real email through Graph.
5. Do not use Power Automate unless Bryan explicitly reintroduces it.
6. Do not clean production data unless Bryan explicitly confirms the new real
   Excel is ready to load and backups/export are handled.

## Commands Worth Knowing

Sync Function modules/scripts:

```bash
.venv/bin/python scripts/sync_function_modules.py
```

Compile local Python:

```bash
.venv/bin/python -m py_compile azure_function_app/function_app.py scripts/sync_function_modules.py azure_function_app/scripts/*.py
```

Safe smoke tests:

```bash
.venv/bin/python scripts/check_function_readiness.py
.venv/bin/python scripts/smoke_e2e_pipeline.py
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```

Function deploy, only if Bryan asks:

```bash
cd azure_function_app
zip -r /tmp/mex-intern-pipeline.zip . \
  -x '*.pyc' '__pycache__/*' '*/__pycache__/*' '.DS_Store' \
     'local.settings.json' '.env' '.venv/*'

az functionapp deployment source config-zip \
  --resource-group rg-intern-pipeline-dev \
  --name mex-intern-pipeline-func-win \
  --src /tmp/mex-intern-pipeline.zip
```

## Cautions

- Do not print secrets.
- Do not enable `SEND_EMAILS=true` yet.
- Do not enable `ENABLE_ADMIN_SQL_SETUP=true` unless intentionally rerunning DB
  setup.
- The local Azure CLI has a known `pyexpat`/XML issue for some Storage data-plane
  operations. Prefer ARM/management-plane commands where possible.
- Local direct SQL connectivity may fail due corporate network/firewall; running
  setup/verification inside Azure worked.
