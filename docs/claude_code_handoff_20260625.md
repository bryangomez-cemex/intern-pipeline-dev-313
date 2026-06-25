# Claude Code Handoff - Changes Made In This Chat

Date: 2026-06-25  
Repo: `/Users/bryangomezcemex/intern-system-pipeline`  
Branch: `codex/intern-pipeline-production-readiness`

This file is a changes-only handoff. It is not an explanation of the whole
system. The system already existed and had worked before this chat. The notes
below only summarize what Codex changed, configured, verified, or documented
during this specific conversation.

Do not print secrets. Do not enable real email sending unless Bryan explicitly
asks.

## Git Commits Created During This Chat

- `d84ca23 Implement intern pipeline production readiness`
- `e9f003b Add baja transition communications`
- `eeef3c8 Add fresh Azure SQL setup support`
- `a9aedc8 Document Claude handoff and fresh Azure setup`
- `b3abc8c Clarify Claude handoff scope`

## Business Logic Changes

### Package 1 Requirements

Changed Package 1 rules to match Bryan's updated HR requirement:

- Use the Spanish label `Paquete 1`.
- Professional photo is no longer required.
- `COMPROBANTE_DOMICILIO` is now required.
- Emergency contact is expected to be captured from email/body text when
  available.
- Package 1 required documents are now aligned around:
  - `ALTA`
  - `CURP`
  - `CONSTANCIA_ESTUDIOS`
  - `IDENTIFICACION`
  - `COMPROBANTE_DOMICILIO`

Related SQL:

- `scripts/sql/2026-06_package1_document_requirements.sql`

### CEMEX HR Relationship Matching

Added/implemented relationship logic for these fields:

- `CIA HC`
- `VP HC`
- `CC HC`
- `OI HC`
- `JefeInmediato`

Main hierarchy:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

Strongest relation signals:

- `JefeInmediato -> VP HC`
- `JefeInmediato -> CC HC`
- `JefeInmediato -> OI HC`
- `JefeInmediato -> CIA HC`
- `OI HC -> VP HC`
- `OI HC -> CC HC`
- `CC HC -> VP HC`
- `CC HC -> CIA HC`

Behavior requested by Bryan:

- If one of these fields is empty, infer/fill it using the strongest available
  relation for that row.
- Use historical intern data and manager assignment data as matching signals.

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`
- `scripts/matching_engine.py`
- `azure_function_app/scripts/matching_engine.py`
- `scripts/sql/create_matching_engine_v1.sql`

### Sequential ID Concurrency Safety

Changed sequential ID generation to be safer for parallel triggers by using SQL
application locks around prefix-based sequential ID creation.

Intent:

- Avoid duplicate sequential IDs when several files/events run at the same time.
- Keep existing ID style while reducing race-condition risk.

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`

### Baja Automation

Added baja transition handling.

Behavior:

- Detect when an intern changes from active/activo/ST002 to inactive/baja.
- Reflect the status change so the intern stops appearing as active.
- Create a lifecycle event for the baja.
- Prepare an HR communication for the baja process.

Prepared HR email subject:

```text
Baja De Practicante - [NOMBRE DE PRACTICANTE]
```

Prepared HR email body fields:

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

Real email sending remains off unless Bryan explicitly enables it.

Related files:

- `scripts/pipeline_service.py`
- `azure_function_app/scripts/pipeline_service.py`
- `scripts/smoke_e2e_pipeline.py`
- `docs/email_alert_recommendations.md`
- `docs/technical_manual.md`

### Expired Active Contracts Report

Added a script to prepare/send a report of active interns with expired
contracts.

Related file:

- `scripts/send_expired_active_contracts_email.py`

Important:

- This can involve PII.
- Keep real sending disabled until Bryan explicitly approves the recipient and
  email provider route.

## Azure / Runtime Configuration Changes

### Document Intelligence

Confirmed that Azure Document Intelligence settings exist in Function App
settings:

- `DOC_INTEL_ENDPOINT`
- `DOC_INTEL_KEY`

The key value must not be printed or committed.

Purpose:

- Scanned PDFs/images can use Document Intelligence.
- Text-layer PDFs can still use local PDF parsing.

### Email Safety Settings

Confirmed and/or set safe email behavior:

- `EMAIL_MODE=simulation`
- `SEND_EMAILS=false`
- `EMAIL_PROVIDER=simulation`

No real email sending should happen with these settings.

### SQL Connection String Fix

Fixed the Azure SQL connection setting issue.

Observed problem:

- `AZURE_SQL_CONNECTION_STRING` existed but had a malformed server key
  (`erver=` instead of `Server=`).
- The connection string also needed the compatible ODBC driver form.

Resolution:

- Reconstructed the setting without printing secrets.
- Used `Driver={ODBC Driver 18 for SQL Server}`.
- Preserved the proper server, database, username, and password values.

## Azure SQL Changes

### Added Base Compatibility Scripts

The previous working environment already had some base tables. The newer Azure
SQL database did not yet have those base objects, so some existing scripts/views
failed until base compatibility tables were added.

Added:

- `scripts/sql/00_create_core_legacy_tables.sql`
- `scripts/sql/00_create_dim_interns.sql`

These create the base objects needed by the existing code/views:

- `dim_interns`
- `fact_files`
- `fact_validations`
- `fact_communications`
- `dim_validation_rules`

Synced copies were also added under:

- `azure_function_app/sql/`

### Correct SQL Order For Empty New Azure SQL DB

When configuring an empty Azure SQL database for this existing system, the
working order is:

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

Reason for this order:

- `dim_interns`, `fact_files`, `fact_validations`, `fact_communications`, and
  `dim_validation_rules` must exist before the views that reference them.
- `2026-06_onboarding_schema.sql` must run before
  `2026-06_schema_simplification.sql` because schema simplification references
  onboarding document tables.

### SQL Verification Result

Verification result after SQL setup:

- `dbo_tables = 30`
- `dbo_views = 41`
- Missing required Power BI views: none.

Verified required Power BI views:

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

## Function App Code Changes

### SQL Setup Helper Guard

Added guarded SQL setup helpers in:

- `azure_function_app/function_app.py`

Added:

- `setup_database`
- `setup_database_on_startup`
- `run_database_setup`
- `split_sql_batches`
- `SQL_SETUP_ORDER`

Guard setting:

```text
ENABLE_ADMIN_SQL_SETUP=false
```

Current expected state:

- `ENABLE_ADMIN_SQL_SETUP=false`

Do not enable this unless Bryan explicitly wants to rerun setup/migrations.

### SQL Scripts Included In Function App Package Folder

Updated sync behavior so SQL scripts are copied into:

- `azure_function_app/sql/`

Related file:

- `scripts/sync_function_modules.py`

## Operational Utility Scripts Added

Added:

- `scripts/run_azure_sql_setup_container.py`
- `scripts/run_azure_sql_verify_container.py`

Purpose:

- Run SQL setup/verification from inside Azure when local SQL connectivity is
  blocked by corporate network/firewall.
- Redact secrets in command output.

Important:

- These scripts are operational helpers.
- Do not run them casually.
- Do not print secrets.

## Power BI / Reporting Changes

Added or refined SQL views for Bryan's no-DAX Power BI setup.

Primary requested reporting areas:

- Vacantes
- Costos
- Inactivos
- Max Per VP
- Contract risk / termination risk
- Missing documents
- HR action queue

Important views:

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

## Data Work Done During This Chat

The up-to-date intern spreadsheet Bryan sent had 3 sheets.

Observed processed counts from the prior environment pass:

- 302 interns total.
- 281 active.
- 21 inactive.

Stale missing-document items from test data were cleaned in the prior
environment pass. Remaining exceptions were contract-risk style warnings, not
Package 1 missing-document requirements.

## Documentation Changes Made

Updated:

- `README.md`
- `docs/technical_manual.md`
- `docs/email_alert_recommendations.md`
- `docs/schema_simplification.md`
- `docs/power_bi_no_dax_5_pages.md`
- `docs/claude_code_handoff_20260625.md`

This handoff file should remain a changes-only summary, not a general project
introduction.

## What Still Needs Care

- Real email sending is still intentionally off.
- Do not enable real SMTP/Graph sending without Bryan's explicit instruction.
- Do not use Power Automate unless Bryan explicitly reintroduces it.
- Do not clean or overwrite real production data unless Bryan explicitly asks
  and confirms backups/export are handled.
- Do not expose secrets.
- Local direct SQL connectivity may fail under corporate network/firewall.
- The local Azure CLI has a known XML/`pyexpat` issue for some Storage data-plane
  commands; management-plane commands worked better.

## Useful Local Verification Commands

Sync Function modules/scripts:

```bash
.venv/bin/python scripts/sync_function_modules.py
```

Compile local Python:

```bash
.venv/bin/python -m py_compile azure_function_app/function_app.py scripts/sync_function_modules.py azure_function_app/scripts/*.py
```

Safe smoke checks:

```bash
.venv/bin/python scripts/check_function_readiness.py
.venv/bin/python scripts/smoke_e2e_pipeline.py
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```
