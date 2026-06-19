# Lifecycle Requirements

MVP 9B adds lifecycle requirements and missing item tracking on top of flexible file classification.

## Process Types

- `PROC_ALTA`: new intern alta package.
- `PROC_EXTENSION`: extendimiento or contract/convenio extension.
- `PROC_BAJA`: termination, baja, or inactive update.
- `PROC_NEW_HIRE`: accepted hires intake.
- `PROC_CURRENT_SYNC`: current interns/practicantes actuales sync.
- `PROC_DOCUMENT_REFRESH`: missing or expired document refresh.
- `PROC_CONTRACT_ALERT`: upcoming convenio/contract expiration alert.
- `PROC_REQUISITION`: general requisition, position creation, or OI/CC/manager/status change.
- `PROC_UNKNOWN`: unknown file or process needing review.

## Required Documents

Seeded document requirements live in `dim_required_document_types` and `fact_process_requirements`.

- New hire requires CV, ID/INE, NDA, school proof, and accepted hires file.
- Alta requires requisition file, accepted hires file, ID/INE, and school proof.
- Extension requires convenio and extension support.
- Baja can include a baja support file if available.
- Current sync requires the current interns file.
- Document refresh is used for missing or expired documents.

## Required Fields

For `PROC_NEW_HIRE` and `PROC_ALTA`:

- Full name or first name
- University
- Career
- Start date
- End date
- Status
- Email can be mapped and stored when present, but is not required in this fake-data MVP.

For `PROC_CURRENT_SYNC`:

- At least one stable identifier: employee number, CEMEX employee number, email, CURP, or RFC
- Status
- End date when active
- OI HC
- CC HC

For `PROC_EXTENSION`:

- Stable intern identifier
- End date
- Status

For `PROC_BAJA`:

- Stable intern identifier
- Status

General validations:

- Start date must be before or equal to end date.
- Active interns with expired end dates create warnings.
- End dates within 30 days create `UPCOMING_EXPIRATION` warnings.

## Missing Item Logging

Missing items are stored in `fact_intern_missing_items`.

Missing types:

- `DataField`
- `Document`
- `Validation`
- `BusinessRule`

Statuses:

- `Open`
- `Resolved`
- `Ignored`

The processor logs missing items and includes them in generated error reports. Blocking missing data prevents row insert/update for flexible lifecycle files. Warning-level items are logged and included in the report, but do not block row update by themselves.

## Communications

If validation or missing-item issues exist:

- A correction communication is prepared for the applicant/new hire or reviewer.
- The generated error report includes validation errors and missing lifecycle items.

If validation passes and there are no missing items:

- HR package communication is prepared.
- Coparmex communication is prepared for Coparmex-required files only in the future production version.
- Applicant/new hire confirmation is prepared.

The current email scripts remain dev-safe:

- `send_prepared_communications.py` only simulates.
- `send_real_dev_email_smtp.py` only sends already-simulated messages to `DEV_EMAIL_OVERRIDE`.

## Power BI

Add these fields/tables to operational dashboards:

- `fact_intern_missing_items.status`
- `fact_intern_missing_items.missing_type`
- `fact_intern_missing_items.missing_code`
- `fact_intern_missing_items.severity`
- `fact_intern_missing_items.process_type_id`
- `fact_intern_lifecycle_events.event_type`
- `fact_intern_lifecycle_events.event_status`
- `fact_file_classification.detected_file_profile_id`
- `fact_detected_columns.canonical_field_name`
- `fact_pipeline_runs.status`

Recommended dashboard visuals:

- Open missing items by process type
- Missing documents by document code
- Current interns with upcoming expiration
- Current interns with expired active end dates
- Validation failures by file profile
- Files needing review

