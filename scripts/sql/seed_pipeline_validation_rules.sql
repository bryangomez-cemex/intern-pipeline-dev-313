IF OBJECT_ID('dbo.dim_validation_rules', 'U') IS NOT NULL
BEGIN
    MERGE dbo.dim_validation_rules AS target
    USING (
        VALUES
            ('VR020', 'Stable Identifier Required', 'Intern Row Validation', 'stable_identifier', 'Error', 'Current intern rows require a stable identifier.', 'No reliable identifier found for current intern row.', 'Add employee number, CEMEX employee number, CURP, RFC, or NSS.'),
            ('VR021', 'Readable File Metadata', 'File Classification', 'file_metadata', 'Error', 'Tabular file metadata must be readable.', 'Could not read tabular file metadata.', 'Confirm the file opens correctly and matches an allowed Excel or CSV format.'),
            ('VR022', 'Classification Needs Review', 'File Classification', 'file_classification', 'Warning', 'File classification needs manual review.', 'File was stored but could not be confidently classified.', 'Review the file manually or rename it with a recognizable document or process type.'),
            ('VR030', 'Known Current Intern Status', 'Intern Row Validation', 'Estatus', 'Error', 'Current intern status must be recognized.', 'Unknown current intern status.', 'Use active/activo, inactive/inactivo, baja, pending/pendiente, or extension pending.'),
            ('VR031', 'Active Intern End Date Valid', 'Intern Row Validation', 'FechaContratoVence', 'Error', 'Active intern cannot have an expired contract end date.', 'Active intern has an expired contract/convenio end date.', 'Confirm baja, extension, or corrected end date.'),
            ('VR032', 'Current Intern Match Required', 'Intern Row Validation', 'intern_match', 'Error', 'Current intern row must match exactly one existing intern.', 'Could not safely match current intern row.', 'Review stable identifiers before updating current intern records.'),
            ('DataField', 'Compatibility: Data Field Missing', 'Lifecycle Requirement', 'DataField', 'Error', 'Compatibility rule for previously deployed pipeline versions.', 'A required lifecycle data field is missing.', 'Deploy the updated pipeline and provide the missing field.'),
            ('BusinessRule', 'Compatibility: Business Rule Missing', 'Lifecycle Requirement', 'BusinessRule', 'Error', 'Compatibility rule for previously deployed pipeline versions.', 'A required lifecycle business rule failed.', 'Deploy the updated pipeline and correct the business field.'),
            ('Validation', 'Compatibility: Lifecycle Validation', 'Lifecycle Requirement', 'Validation', 'Error', 'Compatibility rule for previously deployed pipeline versions.', 'A lifecycle validation failed.', 'Deploy the updated pipeline and correct the validation issue.'),
            ('Document', 'Compatibility: Document Missing', 'Lifecycle Requirement', 'Document', 'Error', 'Compatibility rule for previously deployed pipeline versions.', 'A required lifecycle document is missing.', 'Deploy the updated pipeline and provide the document.')
    ) AS source (
        validation_rule_id,
        rule_name,
        rule_category,
        applies_to,
        severity,
        description,
        error_message_template,
        suggested_fix_template
    )
        ON target.validation_rule_id = source.validation_rule_id
    WHEN MATCHED THEN
        UPDATE SET
            rule_name = source.rule_name,
            rule_category = source.rule_category,
            applies_to = source.applies_to,
            severity = source.severity,
            description = source.description,
            error_message_template = source.error_message_template,
            suggested_fix_template = source.suggested_fix_template,
            active_flag = 1
    WHEN NOT MATCHED THEN
        INSERT (
            validation_rule_id,
            rule_name,
            rule_category,
            applies_to,
            severity,
            description,
            error_message_template,
            suggested_fix_template,
            active_flag
        )
        VALUES (
            source.validation_rule_id,
            source.rule_name,
            source.rule_category,
            source.applies_to,
            source.severity,
            source.description,
            source.error_message_template,
            source.suggested_fix_template,
            1
        );
END;
GO
