# Database Schema Inventory

Source: local SQL migrations plus Azure object names/selected live columns confirmed during readiness cleanup on 2026-06-24.

Tables: 39
Views: 22

## Tables

### dim_canonical_fields
- `canonical_field_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `canonical_field_name`: `NVARCHAR(255) NOT NULL`
- `field_group`: `NVARCHAR(100) NULL`
- `data_type`: `NVARCHAR(50) NULL`
- `description`: `NVARCHAR(MAX) NULL`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_column_aliases
- `column_alias_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `canonical_field_id`: `NVARCHAR(50) NOT NULL`
- `alias_name`: `NVARCHAR(255) NOT NULL`
- `normalized_alias_name`: `NVARCHAR(255) NOT NULL`
- `source_profile`: `NVARCHAR(255) NULL`
- `confidence`: `DECIMAL(5, 4) NOT NULL DEFAULT 1.0`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_communication_templates
- `template_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `template_name`: `NVARCHAR(100) NOT NULL`
- `recipient_group_id`: `NVARCHAR(50) NULL`
- `subject_template`: `NVARCHAR(255) NULL`
- `body_template`: `NVARCHAR(MAX) NULL`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_document_types
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_email_recipients
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_email_templates
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_file_profiles
- `file_profile_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `profile_name`: `NVARCHAR(255) NOT NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `expected_extension`: `NVARCHAR(20) NULL`
- `row_processable`: `BIT NOT NULL DEFAULT 0`
- `description`: `NVARCHAR(MAX) NULL`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_file_status
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_file_types
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_interns
- `email_personal`: `NVARCHAR(200) NULL`
- `telefono`: `NVARCHAR(50) NULL`
- `estado_civil`: `NVARCHAR(50) NULL`
- `nacionalidad`: `NVARCHAR(50) NULL`
- `matricula`: `NVARCHAR(50) NULL`
- `grado`: `NVARCHAR(100) NULL`
- `fecha_nacimiento`: `DATE NULL`
- `calle`: `NVARCHAR(200) NULL`
- `numero_exterior`: `NVARCHAR(50) NULL`
- `colonia`: `NVARCHAR(150) NULL`
- `poblacion`: `NVARCHAR(150) NULL`
- `estado_direccion`: `NVARCHAR(100) NULL`
- `codigo_postal`: `NVARCHAR(20) NULL`
- `requisition_id`: `NVARCHAR(50) NULL`
- `candidate_source_blob`: `NVARCHAR(400) NULL`
- `candidate_needs_review`: `BIT NULL`
- `candidate_validation_notes`: `NVARCHAR(MAX) NULL`
- `cemex_id`: `NVARCHAR(50) NULL`
- `correo_institucional`: `NVARCHAR(200) NULL`
- `ubicacion_udn`: `NVARCHAR(150) NULL`
- `compania`: `NVARCHAR(150) NULL`
- `ubicacion_estado`: `NVARCHAR(100) NULL`
- `oi`: `NVARCHAR(50) NULL`
- `cc`: `NVARCHAR(50) NULL`
- `fecha_graduacion`: `NVARCHAR(50) NULL`
- `hr_list_matched`: `BIT NULL`
- `apodo`: `NVARCHAR(100) NULL`
- `linkedin`: `NVARCHAR(300) NULL`
- `contacto_emergencia`: `NVARCHAR(500) NULL`
- `documents_status`: `NVARCHAR(40) NULL`
- `convenio_status`: `NVARCHAR(40) NULL`

### dim_lifecycle_processes
- `process_type_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `process_type_name`: `NVARCHAR(100) NOT NULL`
- `description`: `NVARCHAR(MAX) NULL`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_manager_assignments
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_process_types
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_recipient_groups
- `recipient_group_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `recipient_group_name`: `NVARCHAR(100) NOT NULL`
- `description`: `NVARCHAR(MAX) NULL`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_required_document_types
- `required_document_type_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `document_code`: `NVARCHAR(100) NOT NULL`
- `document_name`: `NVARCHAR(255) NOT NULL`
- `description`: `NVARCHAR(MAX) NULL`
- `allowed_file_extensions`: `NVARCHAR(255) NULL`
- `required_for_coparmex`: `BIT NOT NULL DEFAULT 0`
- `required_for_hr`: `BIT NOT NULL DEFAULT 0`
- `required_for_applicant`: `BIT NOT NULL DEFAULT 0`
- `is_active`: `BIT NOT NULL DEFAULT 1`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### dim_requirements
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_requisitions
- `puesto`: `NVARCHAR(300) NULL`
- `direccion`: `NVARCHAR(200) NULL`
- `region_area`: `NVARCHAR(200) NULL`
- `asesor_rh`: `NVARCHAR(200) NULL`
- `manager_email`: `NVARCHAR(200) NULL`
- `carrera_requerida`: `NVARCHAR(200) NULL`
- `semestre_requerido`: `NVARCHAR(50) NULL`
- `disponibilidad_horario`: `NVARCHAR(200) NULL`
- `periodo_estadia`: `NVARCHAR(100) NULL`
- `fecha_inicio_solicitada`: `DATE NULL`
- `fecha_termino_solicitada`: `DATE NULL`
- `descripcion_proyecto`: `NVARCHAR(MAX) NULL`
- `retos`: `NVARCHAR(MAX) NULL`
- `responsabilidades`: `NVARCHAR(MAX) NULL`
- `entregables`: `NVARCHAR(MAX) NULL`
- `habilidades`: `NVARCHAR(MAX) NULL`
- `modalidad`: `NVARCHAR(50) NULL`
- `prioridad`: `NVARCHAR(50) NULL`
- `convenio_requerido`: `BIT NULL`
- `needs_review`: `BIT NULL`
- `parse_notes`: `NVARCHAR(MAX) NULL`
- `source_container`: `NVARCHAR(200) NULL`
- `source_blob_name`: `NVARCHAR(400) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `requisition_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `requisition_type`: `NVARCHAR(100) NULL`
- `requisition_status`: `NVARCHAR(100) NULL`
- `requested_by`: `NVARCHAR(255) NULL`
- `vp_hc`: `NVARCHAR(255) NULL`
- `area`: `NVARCHAR(255) NULL`
- `manager`: `NVARCHAR(255) NULL`
- `oi_hc`: `NVARCHAR(255) NULL`
- `cc_hc`: `NVARCHAR(255) NULL`
- `company`: `NVARCHAR(255) NULL`
- `requested_start_date`: `DATE NULL`
- `requested_end_date`: `DATE NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `updated_at`: `DATETIME2 NULL`

### dim_status
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### dim_validation_rules
- `validation_rule_id`: `confirmed in Azure; type not re-queried after approval limit`
- `rule_name`: `confirmed in Azure; type not re-queried after approval limit`
- `rule_category`: `confirmed in Azure; type not re-queried after approval limit`
- `applies_to`: `confirmed in Azure; type not re-queried after approval limit`
- `severity`: `confirmed in Azure; type not re-queried after approval limit`
- `description`: `confirmed in Azure; type not re-queried after approval limit`
- `error_message_template`: `confirmed in Azure; type not re-queried after approval limit`
- `suggested_fix_template`: `confirmed in Azure; type not re-queried after approval limit`
- `active_flag`: `confirmed in Azure; type not re-queried after approval limit`
- `created_at`: `confirmed in Azure; type not re-queried after approval limit`

### fact_communication_package_files
- `package_file_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `package_id`: `NVARCHAR(50) NOT NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `blob_container`: `NVARCHAR(255) NULL`
- `blob_path`: `NVARCHAR(1000) NULL`
- `document_code`: `NVARCHAR(100) NULL`
- `recipient_group_id`: `NVARCHAR(50) NULL`
- `include_reason`: `NVARCHAR(MAX) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `source_file_id`: `NVARCHAR(50) NULL`

### fact_communication_packages
- `package_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `communication_id`: `NVARCHAR(50) NULL`
- `intern_id`: `NVARCHAR(50) NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `recipient_group_id`: `NVARCHAR(50) NOT NULL`
- `package_status`: `NVARCHAR(50) NOT NULL DEFAULT 'Prepared'`
- `summary_text`: `NVARCHAR(MAX) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `sent_at`: `DATETIME2 NULL`

### fact_communications
- `email_type`: `NVARCHAR(100) NULL`
- `sent_to`: `NVARCHAR(255) NULL`
- `status`: `NVARCHAR(100) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `email_template_id`: `NVARCHAR(50) NULL`
- `communication_type`: `NVARCHAR(100) NULL`
- `recipient_group`: `NVARCHAR(100) NULL`
- `recipient_email`: `NVARCHAR(255) NULL`
- `subject`: `NVARCHAR(255) NULL`
- `body`: `NVARCHAR(MAX) NULL`
- `communication_status`: `NVARCHAR(100) NULL`
- `error_message`: `NVARCHAR(MAX) NULL`
- `sent_at`: `DATETIME2 NULL`
- `last_attempt_at`: `DATETIME2 NULL`
- `provider_message_id`: `NVARCHAR(255) NULL`
- `send_attempts`: `INT NOT NULL DEFAULT 0`
- `communication_id`: `confirmed in Azure; type not re-queried after approval limit`
- `intern_id`: `confirmed in Azure; type not re-queried after approval limit`
- `requisition_id`: `confirmed in Azure; type not re-queried after approval limit`
- `cc`: `confirmed in Azure; type not re-queried after approval limit`
- `attachments_included`: `confirmed in Azure; type not re-queried after approval limit`
- `created_at`: `confirmed in Azure; type not re-queried after approval limit`

### fact_detected_columns
- `detected_column_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `run_id`: `NVARCHAR(50) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `source_container`: `NVARCHAR(255) NULL`
- `source_blob_name`: `NVARCHAR(1000) NULL`
- `sheet_name`: `NVARCHAR(255) NULL`
- `ordinal_position`: `INT NULL`
- `source_column_name`: `NVARCHAR(255) NOT NULL`
- `normalized_column_name`: `NVARCHAR(255) NULL`
- `canonical_field_id`: `NVARCHAR(50) NULL`
- `canonical_field_name`: `NVARCHAR(255) NULL`
- `source_profile`: `NVARCHAR(255) NULL`
- `mapping_confidence`: `DECIMAL(5, 4) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `source_file_id`: `NVARCHAR(50) NULL`

### fact_entity_matches
- `entity_match_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `run_id`: `NVARCHAR(50) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `source_row_number`: `INT NULL`
- `source_entity_type`: `NVARCHAR(100) NULL`
- `matched_entity_type`: `NVARCHAR(100) NULL`
- `matched_entity_id`: `NVARCHAR(100) NULL`
- `match_score`: `DECIMAL(5, 2) NOT NULL DEFAULT 0`
- `match_confidence`: `NVARCHAR(50) NOT NULL`
- `match_method`: `NVARCHAR(255) NULL`
- `evidence_used`: `NVARCHAR(MAX) NULL`
- `alternative_matches`: `NVARCHAR(MAX) NULL`
- `needs_review`: `BIT NOT NULL DEFAULT 1`
- `conflict_reason`: `NVARCHAR(MAX) NULL`
- `status`: `NVARCHAR(50) NOT NULL DEFAULT 'Proposed'`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `updated_at`: `DATETIME2 NULL`

### fact_file_classification
- `classification_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `run_id`: `NVARCHAR(50) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `source_container`: `NVARCHAR(255) NOT NULL`
- `source_blob_name`: `NVARCHAR(1000) NOT NULL`
- `file_name`: `NVARCHAR(1000) NULL`
- `file_extension`: `NVARCHAR(20) NULL`
- `mime_type`: `NVARCHAR(255) NULL`
- `sheet_names`: `NVARCHAR(MAX) NULL`
- `detected_column_count`: `INT NULL`
- `detected_file_profile_id`: `NVARCHAR(50) NULL`
- `detected_document_type_id`: `NVARCHAR(50) NULL`
- `detected_process_type_id`: `NVARCHAR(50) NULL`
- `classification_confidence`: `DECIMAL(5, 4) NULL`
- `classification_reason`: `NVARCHAR(MAX) NULL`
- `needs_review`: `BIT NOT NULL DEFAULT 0`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `source_file_id`: `NVARCHAR(50) NULL`

### fact_files
- `file_id`: `confirmed in Azure; type not re-queried after approval limit`
- `intern_id`: `confirmed in Azure; type not re-queried after approval limit`
- `requisition_id`: `confirmed in Azure; type not re-queried after approval limit`
- `document_type_id`: `confirmed in Azure; type not re-queried after approval limit`
- `file_type_id`: `confirmed in Azure; type not re-queried after approval limit`
- `file_status_id`: `confirmed in Azure; type not re-queried after approval limit`
- `original_file_name`: `confirmed in Azure; type not re-queried after approval limit`
- `stored_file_name`: `confirmed in Azure; type not re-queried after approval limit`
- `file_extension`: `confirmed in Azure; type not re-queried after approval limit`
- `mime_type`: `confirmed in Azure; type not re-queried after approval limit`
- `file_size_bytes`: `confirmed in Azure; type not re-queried after approval limit`
- `blob_container`: `confirmed in Azure; type not re-queried after approval limit`
- `blob_path`: `confirmed in Azure; type not re-queried after approval limit`
- `uploaded_by_email`: `confirmed in Azure; type not re-queried after approval limit`
- `received_from_email`: `confirmed in Azure; type not re-queried after approval limit`
- `received_date`: `confirmed in Azure; type not re-queried after approval limit`
- `validation_status`: `confirmed in Azure; type not re-queried after approval limit`
- `error_message`: `confirmed in Azure; type not re-queried after approval limit`
- `send_to_hr`: `confirmed in Azure; type not re-queried after approval limit`
- `send_to_coparmex`: `confirmed in Azure; type not re-queried after approval limit`
- `created_at`: `confirmed in Azure; type not re-queried after approval limit`

### fact_hires
- `hire_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `intern_id`: `NVARCHAR(50) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `source_row_number`: `INT NULL`
- `hire_status`: `NVARCHAR(100) NULL`
- `onboarding_status`: `NVARCHAR(100) NULL`
- `accepted_at`: `DATETIME2 NULL`
- `start_date`: `DATE NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `file_id`: `NVARCHAR(50) NULL`

### fact_intern_beneficiaries
- `beneficiary_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY, intern_id NVARCHAR(50) NULL`
- `nombre`: `NVARCHAR(150) NULL, paterno NVARCHAR(150) NULL, materno NVARCHAR(150) NULL`
- `parentesco`: `NVARCHAR(50) NULL, porcentaje NVARCHAR(20) NULL`
- `source_blob`: `NVARCHAR(400) NULL, created_at DATETIME2 DEFAULT SYSUTCDATETIME());`
- `IF`: `OBJECT_ID('dbo.dim_manager_assignments','U') IS NULL`
- `CREATE`: `TABLE dbo.dim_manager_assignments (`
- `jefe_key`: `NVARCHAR(300) NOT NULL PRIMARY KEY, jefe_directo NVARCHAR(200) NULL`
- `vp`: `NVARCHAR(200) NULL, asesor_rh NVARCHAR(200) NULL, ubicacion_udn NVARCHAR(200) NULL`
- `estado`: `NVARCHAR(100) NULL, compania NVARCHAR(200) NULL, oi NVARCHAR(50) NULL`
- `cc`: `NVARCHAR(50) NULL, updated_at DATETIME2 DEFAULT SYSUTCDATETIME());`
- `document_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY, intern_id NVARCHAR(50) NULL`
- `stage`: `NVARCHAR(30) NULL, document_type NVARCHAR(40) NULL, file_name NVARCHAR(300) NULL`
- `blob_path`: `NVARCHAR(400) NULL, name_match BIT NULL, extracted NVARCHAR(MAX) NULL`
- `status`: `NVARCHAR(40) NULL, notes NVARCHAR(MAX) NULL, created_at DATETIME2 DEFAULT SYSUTCDATETIME());`

### fact_intern_document_status
- `intern_document_status_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `intern_id`: `NVARCHAR(50) NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `document_type_id`: `NVARCHAR(50) NOT NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `status`: `NVARCHAR(50) NOT NULL`
- `validation_status`: `NVARCHAR(100) NULL`
- `is_required`: `BIT NOT NULL DEFAULT 0`
- `is_missing`: `BIT NOT NULL DEFAULT 0`
- `is_expired`: `BIT NOT NULL DEFAULT 0`
- `expires_at`: `DATETIME2 NULL`
- `reviewed_at`: `DATETIME2 NULL`
- `notes`: `NVARCHAR(MAX) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `updated_at`: `DATETIME2 NULL`
- `source_file_id`: `NVARCHAR(50) NULL`

### fact_intern_documents
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### fact_intern_lifecycle_events
- `lifecycle_event_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `run_id`: `NVARCHAR(50) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `intern_id`: `NVARCHAR(50) NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `event_type`: `NVARCHAR(100) NOT NULL`
- `event_status`: `NVARCHAR(100) NOT NULL`
- `event_date`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `source_row_number`: `INT NULL`
- `old_status`: `NVARCHAR(100) NULL`
- `new_status`: `NVARCHAR(100) NULL`
- `message`: `NVARCHAR(MAX) NULL`
- `needs_review`: `BIT NOT NULL DEFAULT 0`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `source_file_id`: `NVARCHAR(50) NULL`

### fact_intern_missing_items
- `missing_item_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `intern_id`: `NVARCHAR(50) NULL`
- `process_type_id`: `NVARCHAR(50) NULL`
- `missing_type`: `NVARCHAR(50) NOT NULL`
- `missing_code`: `NVARCHAR(100) NOT NULL`
- `missing_description`: `NVARCHAR(MAX) NOT NULL`
- `severity`: `NVARCHAR(50) NOT NULL`
- `status`: `NVARCHAR(50) NOT NULL DEFAULT 'Open'`
- `source_file_id`: `NVARCHAR(50) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `resolved_at`: `DATETIME2 NULL`
- `file_id`: `NVARCHAR(50) NULL`

### fact_match_candidates
- `match_candidate_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `entity_match_id`: `NVARCHAR(50) NULL`
- `candidate_rank`: `INT NULL`
- `candidate_entity_type`: `NVARCHAR(100) NULL`
- `candidate_entity_id`: `NVARCHAR(100) NULL`
- `candidate_score`: `DECIMAL(5, 2) NOT NULL DEFAULT 0`
- `candidate_confidence`: `NVARCHAR(50) NOT NULL`
- `match_method`: `NVARCHAR(255) NULL`
- `evidence_used`: `NVARCHAR(MAX) NULL`
- `conflict_reason`: `NVARCHAR(MAX) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### fact_match_conflicts
- `match_conflict_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `entity_match_id`: `NVARCHAR(50) NULL`
- `run_id`: `NVARCHAR(50) NULL`
- `file_id`: `NVARCHAR(50) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `source_row_number`: `INT NULL`
- `conflict_type`: `NVARCHAR(100) NOT NULL`
- `source_entity_type`: `NVARCHAR(100) NULL`
- `conflicting_entity_type`: `NVARCHAR(100) NULL`
- `conflicting_entity_id`: `NVARCHAR(100) NULL`
- `conflict_reason`: `NVARCHAR(MAX) NOT NULL`
- `evidence_used`: `NVARCHAR(MAX) NULL`
- `severity`: `NVARCHAR(50) NOT NULL DEFAULT 'Error'`
- `status`: `NVARCHAR(50) NOT NULL DEFAULT 'Open'`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `resolved_at`: `DATETIME2 NULL`

### fact_pipeline_runs
- `run_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `run_type`: `NVARCHAR(50) NULL`
- `source_script`: `NVARCHAR(255) NULL`
- `started_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `finished_at`: `DATETIME2 NULL`
- `status`: `NVARCHAR(50) NOT NULL`
- `source_container`: `NVARCHAR(255) NULL`
- `source_blob_name`: `NVARCHAR(1000) NULL`
- `archived_blob_name`: `NVARCHAR(1000) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `error_report_file_id`: `NVARCHAR(50) NULL`
- `communication_id`: `NVARCHAR(50) NULL`
- `good_rows`: `INT NULL`
- `bad_rows`: `INT NULL`
- `total_rows`: `INT NULL`
- `error_message`: `NVARCHAR(MAX) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `file_id`: `NVARCHAR(50) NULL`

### fact_process_requirements
- `requirement_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `process_type_id`: `NVARCHAR(50) NOT NULL`
- `required_document_type_id`: `NVARCHAR(50) NOT NULL`
- `is_required`: `BIT NOT NULL DEFAULT 1`
- `requirement_scope`: `NVARCHAR(100) NULL`
- `created_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`

### fact_processed_blobs
- `processed_blob_id`: `NVARCHAR(50) NOT NULL PRIMARY KEY`
- `source_container`: `NVARCHAR(255) NOT NULL`
- `source_blob_name`: `NVARCHAR(1000) NOT NULL`
- `source_blob_size_bytes`: `BIGINT NULL`
- `source_blob_last_modified`: `DATETIME2 NULL`
- `source_blob_etag`: `NVARCHAR(255) NULL`
- `source_file_id`: `NVARCHAR(50) NULL`
- `run_id`: `NVARCHAR(50) NULL`
- `processed_at`: `DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`
- `archived_blob_name`: `NVARCHAR(1000) NULL`
- `status`: `NVARCHAR(50) NOT NULL`
- `file_id`: `NVARCHAR(50) NULL`

### fact_status_history
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

### fact_validations
- Columns exist in Azure, but this table is not fully declared in the local SQL migration files available offline.

## Views

- `vw_business_validation_exceptions`
- `vw_communications_status`
- `vw_error_reports`
- `vw_full_mvp_communication_packages`
- `vw_full_mvp_detected_columns`
- `vw_full_mvp_document_status`
- `vw_full_mvp_file_classification`
- `vw_full_mvp_interns_current`
- `vw_full_mvp_lifecycle_events`
- `vw_full_mvp_missing_items`
- `vw_full_mvp_package_files`
- `vw_full_mvp_pipeline_runs`
- `vw_full_mvp_pipeline_summary`
- `vw_full_mvp_validation_errors`
- `vw_hr_actions_today`
- `vw_interns_current`
- `vw_matching_engine_conflicts`
- `vw_matching_engine_review_queue`
- `vw_pipeline_files`
- `vw_pipeline_summary`
- `vw_requisitions_status`
- `vw_validation_errors`