IF OBJECT_ID('dbo.fact_files', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_files (
        file_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        document_type_id NVARCHAR(50) NULL,
        file_type_id NVARCHAR(50) NULL,
        file_status_id NVARCHAR(50) NULL,
        original_file_name NVARCHAR(500) NULL,
        stored_file_name NVARCHAR(500) NULL,
        file_extension NVARCHAR(50) NULL,
        mime_type NVARCHAR(255) NULL,
        file_size_bytes BIGINT NULL,
        blob_container NVARCHAR(255) NULL,
        blob_path NVARCHAR(1000) NULL,
        uploaded_by_email NVARCHAR(255) NULL,
        received_from_email NVARCHAR(255) NULL,
        validation_status NVARCHAR(100) NULL,
        error_message NVARCHAR(MAX) NULL,
        send_to_hr BIT NOT NULL DEFAULT 0,
        send_to_coparmex BIT NOT NULL DEFAULT 0,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.dim_validation_rules', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dim_validation_rules (
        validation_rule_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        rule_name NVARCHAR(255) NULL,
        rule_category NVARCHAR(100) NULL,
        applies_to NVARCHAR(255) NULL,
        severity NVARCHAR(50) NULL,
        description NVARCHAR(MAX) NULL,
        error_message_template NVARCHAR(MAX) NULL,
        suggested_fix_template NVARCHAR(MAX) NULL,
        active_flag BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO

IF OBJECT_ID('dbo.fact_validations', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_validations (
        validation_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        intern_id NVARCHAR(50) NULL,
        file_id NVARCHAR(50) NULL,
        validation_rule_id NVARCHAR(50) NULL,
        field_name NVARCHAR(255) NULL,
        validation_type NVARCHAR(100) NULL,
        severity NVARCHAR(50) NULL,
        validation_result NVARCHAR(100) NULL,
        error_message NVARCHAR(MAX) NULL,
        suggested_fix NVARCHAR(MAX) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID('dbo.fact_communications', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.fact_communications (
        communication_id NVARCHAR(50) NOT NULL PRIMARY KEY,
        email_type NVARCHAR(100) NULL,
        sent_to NVARCHAR(255) NULL,
        status NVARCHAR(100) NULL,
        file_id NVARCHAR(50) NULL,
        email_template_id NVARCHAR(50) NULL,
        communication_type NVARCHAR(100) NULL,
        recipient_group NVARCHAR(100) NULL,
        recipient_email NVARCHAR(255) NULL,
        subject NVARCHAR(500) NULL,
        body NVARCHAR(MAX) NULL,
        communication_status NVARCHAR(100) NULL,
        error_message NVARCHAR(MAX) NULL,
        sent_at DATETIME2 NULL,
        last_attempt_at DATETIME2 NULL,
        send_attempts INT NOT NULL DEFAULT 0,
        provider_message_id NVARCHAR(255) NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2 NULL
    );
END;
GO
