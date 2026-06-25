# Changes Made By Codex In This Chat

Date: 2026-06-25  
Repo: `/Users/bryangomezcemex/intern-system-pipeline`  
Branch: `codex/intern-pipeline-production-readiness`

## Commits Created

- `d84ca23 Implement intern pipeline production readiness`
- `e9f003b Add baja transition communications`
- `eeef3c8 Add fresh Azure SQL setup support`
- `a9aedc8 Document Claude handoff and fresh Azure setup`
- `b3abc8c Clarify Claude handoff scope`
- `c1e4083 Make Claude handoff changes-only`

## Azure Resource Changes

Azure account/subscription context used during this chat:

- Account: `bryan.gomez@ext.cemex.com`
- Subscription: `Azure subscription 1`
- Subscription ID: `a3d54e37-bfef-4efb-8f09-f6d848b499c7`
- Tenant ID: `6ee19001-d0c4-45f8-af8b-ff00f16d07e1`

Azure resources confirmed or configured:

- Resource group: `rg-intern-pipeline-dev`
- Function App: `mex-intern-pipeline-func-win`
- Function host: `mex-intern-pipeline-func-win-axgkagdsdgfbebc6.centralus-01.azurewebsites.net`
- SQL server: `rg-intern-system-devbge.database.windows.net`
- SQL database: `rg-intern-system-dev`
- Storage account: `rginternpipelinedevb961`
- Document Intelligence resource: `docintel-intern-pipeline-dev`

Storage containers created or confirmed:

- `raw-uploads`
- `error-reports`
- `archive`

Function App settings confirmed or changed:

- `AZURE_SQL_CONNECTION_STRING`
- `AZURE_SQL_AUTH_MODE=sql_password`
- `AZURE_SQL_SERVER=rg-intern-system-devbge.database.windows.net`
- `AZURE_SQL_DATABASE=rg-intern-system-dev`
- `DOC_INTEL_ENDPOINT`
- `DOC_INTEL_KEY`
- `EMAIL_MODE=simulation`
- `EMAIL_PROVIDER=simulation`
- `SEND_EMAILS=false`
- `ENABLE_ADMIN_SQL_SETUP=false`

Azure SQL firewall/provider work completed:

- Confirmed SQL public network access was enabled.
- Confirmed existing `AllowAllWindowsAzureIps` rule.
- Created and deleted a temporary local SQL firewall rule during troubleshooting.
- Registered Azure provider `Microsoft.ContainerInstance`.

Temporary Azure resources created and removed:

- Azure Container Instance `aci-sql-setup-20260625`.
- Azure Container Instance `aci-sql-verify-20260625`.
- Azure Files shares named `sqlsetup*`.

Azure verification result:

- Function App state: `Running`.
- Indexed functions:
  - `process_raw_upload`
  - `setup_database`
  - `setup_database_on_startup`
- Safety app settings:
  - `EMAIL_MODE=simulation`
  - `SEND_EMAILS=false`
  - `ENABLE_ADMIN_SQL_SETUP=false`

## Package 1

Changed Package 1 requirements:

- Renamed/displayed as `Paquete 1`.
- Removed professional photo requirement.
- Added `COMPROBANTE_DOMICILIO` as required.
- Added support for emergency contact captured from email/body text.
- Package 1 required documents aligned to:
  - `ALTA`
  - `CURP`
  - `CONSTANCIA_ESTUDIOS`
  - `IDENTIFICACION`
  - `COMPROBANTE_DOMICILIO`

Related SQL:

- `scripts/sql/2026-06_package1_document_requirements.sql`

## CEMEX HR Relationship Matching

Added relationship logic for:

- `CIA HC`
- `VP HC`
- `CC HC`
- `OI HC`
- `JefeInmediato`

Main hierarchy:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

Strong relationship signals added:

- `JefeInmediato -> VP HC`
- `JefeInmediato -> CC HC`
- `JefeInmediato -> OI HC`
- `JefeInmediato -> CIA HC`
- `OI HC -> VP HC`
- `OI HC -> CC HC`
- `CC HC -> VP HC`
- `CC HC -> CIA HC`

The matching logic uses existing intern rows and manager assignment rows to fill
or suggest missing organization fields.

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`
- `scripts/matching_engine.py`
- `azure_function_app/scripts/matching_engine.py`
- `scripts/sql/create_matching_engine_v1.sql`

## Sequential IDs

Changed sequential ID creation to use SQL application locks around prefix-based
ID generation.

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`

## Baja Automation

Added baja transition handling.

Behavior added:

- Detect active/activo/ST002 to inactive/baja transitions.
- Update lifecycle/status handling so baja interns no longer count as active.
- Create baja lifecycle events.
- Prepare an HR baja communication.

Prepared email subject:

```text
Baja De Practicante - [NOMBRE DE PRACTICANTE]
```

Prepared email body fields:

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

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`
- `scripts/smoke_e2e_pipeline.py`
- `docs/email_alert_recommendations.md`
- `docs/technical_manual.md`

## Expired Active Contracts Report

Added a script for active interns with expired contracts:

- `scripts/send_expired_active_contracts_email.py`

## Document Intelligence

Confirmed Azure Document Intelligence settings exist in Function App settings:

- `DOC_INTEL_ENDPOINT`
- `DOC_INTEL_KEY`

Document Intelligence support is used for scanned PDFs/images. Text-layer PDFs
can still use local PDF parsing.

## Email Settings

Set or confirmed email-safe settings:

- `EMAIL_MODE=simulation`
- `SEND_EMAILS=false`
- `EMAIL_PROVIDER=simulation`

## SQL Connection String

Fixed the Azure SQL connection setting.

Original issue observed:

- The connection setting had `erver=` instead of `Server=`.
- The connection string needed the compatible ODBC driver form.

Result:

- Reconstructed the SQL connection setting.
- Used `Driver={ODBC Driver 18 for SQL Server}`.
- Preserved the server, database, username, and password values without printing
  the secret.

## Azure SQL Base Compatibility

Added base SQL scripts for the newer Azure SQL database:

- `scripts/sql/00_create_core_legacy_tables.sql`
- `scripts/sql/00_create_dim_interns.sql`

These scripts create base objects used by existing code and views:

- `dim_interns`
- `fact_files`
- `fact_validations`
- `fact_communications`
- `dim_validation_rules`

Synced copies were also added under:

- `azure_function_app/sql/`

## SQL Script Order

Established the working SQL order for an empty Azure SQL database used by this
existing system:

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

Ordering fixes discovered during the chat:

- Base compatibility tables need to exist before views reference them.
- `2026-06_onboarding_schema.sql` needs to run before
  `2026-06_schema_simplification.sql`.

## SQL Verification

Azure SQL verification result:

- `dbo_tables = 30`
- `dbo_views = 41`
- Missing required Power BI views: none.

Verified Power BI views:

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

## Function App SQL Setup Helpers

Added SQL setup helper code in:

- `azure_function_app/function_app.py`

Added functions/constants:

- `setup_database`
- `setup_database_on_startup`
- `run_database_setup`
- `split_sql_batches`
- `SQL_SETUP_ORDER`

Added guard setting used by these helpers:

- `ENABLE_ADMIN_SQL_SETUP`

Current confirmed value:

- `ENABLE_ADMIN_SQL_SETUP=false`

## SQL Sync

Updated sync behavior so SQL scripts copy into:

- `azure_function_app/sql/`

Related file:

- `scripts/sync_function_modules.py`

## Operational Utility Scripts

Added:

- `scripts/run_azure_sql_setup_container.py`
- `scripts/run_azure_sql_verify_container.py`

These scripts were used for SQL setup/verification from inside Azure when local
SQL connectivity was blocked by network/firewall behavior.

## Power BI / Reporting

Added or refined SQL reporting views for Bryan's no-DAX Power BI setup.

Reporting areas covered:

- Vacantes
- Costos
- Inactivos
- Max Per VP
- Contract risk / termination risk
- Missing documents
- HR action queue

Views involved:

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

Related docs:

- `docs/power_bi_no_dax_5_pages.md`
- `docs/power_bi_dashboard.md`
- `docs/schema_simplification.md`

## Data Work

Processed/checked the up-to-date intern spreadsheet Bryan sent.

Observed counts:

- 3 sheets in the spreadsheet.
- 302 interns total.
- 281 active.
- 21 inactive.

Cleaned stale missing-document items from previous test data in the earlier
environment pass.

Remaining exceptions were contract-risk style warnings, not Package 1
missing-document requirements.

## Documentation Updated

Updated:

- `README.md`
- `docs/technical_manual.md`
- `docs/email_alert_recommendations.md`
- `docs/schema_simplification.md`
- `docs/power_bi_no_dax_5_pages.md`
- `docs/claude_code_handoff_20260625.md`
