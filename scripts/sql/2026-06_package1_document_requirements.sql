/*
Paquete 1 document requirements.

This migration aligns document configuration with the current HR onboarding
package:
  - Required: alta, CURP, constancia, identificacion, comprobante de domicilio.
  - Not required: professional photo.
  - Emergency contact is captured as email/body text, not as a document.

The script does not delete historical facts. It deactivates legacy applicant
requirements and resolves old open missing-document items that were generated
from the superseded package.
*/

MERGE dbo.dim_required_document_types AS target
USING (
    VALUES
        ('RDT_ALTA', 'ALTA', 'Alta / candidate information', 'Candidate alta form or spreadsheet with personal data and emergency contact captured from email/body text.', '.xlsx,.csv,.pdf,.docx', 0, 1, 1, 1),
        ('RDT_CURP', 'CURP', 'CURP', 'CURP document or equivalent candidate identity proof.', '.pdf,.png,.jpg,.jpeg', 0, 1, 1, 1),
        ('RDT_CONSTANCIA_ESTUDIOS', 'CONSTANCIA_ESTUDIOS', 'Constancia de estudios', 'Current enrollment or school proof document.', '.pdf,.png,.jpg,.jpeg,.docx', 0, 1, 1, 1),
        ('RDT_IDENTIFICACION', 'IDENTIFICACION', 'Identificacion oficial', 'INE, passport, or equivalent official identification.', '.pdf,.png,.jpg,.jpeg', 0, 1, 1, 1),
        ('RDT_COMPROBANTE_DOMICILIO', 'COMPROBANTE_DOMICILIO', 'Comprobante de domicilio', 'Recent proof of address such as CFE, water, phone, or similar utility receipt.', '.pdf,.png,.jpg,.jpeg', 0, 1, 1, 1)
) AS source (
    required_document_type_id,
    document_code,
    document_name,
    description,
    allowed_file_extensions,
    required_for_coparmex,
    required_for_hr,
    required_for_applicant,
    is_active
)
    ON target.required_document_type_id = source.required_document_type_id
WHEN MATCHED THEN
    UPDATE SET
        document_code = source.document_code,
        document_name = source.document_name,
        description = source.description,
        allowed_file_extensions = source.allowed_file_extensions,
        required_for_coparmex = source.required_for_coparmex,
        required_for_hr = source.required_for_hr,
        required_for_applicant = source.required_for_applicant,
        is_active = source.is_active
WHEN NOT MATCHED THEN
    INSERT (
        required_document_type_id,
        document_code,
        document_name,
        description,
        allowed_file_extensions,
        required_for_coparmex,
        required_for_hr,
        required_for_applicant,
        is_active
    )
    VALUES (
        source.required_document_type_id,
        source.document_code,
        source.document_name,
        source.description,
        source.allowed_file_extensions,
        source.required_for_coparmex,
        source.required_for_hr,
        source.required_for_applicant,
        source.is_active
    );
GO

UPDATE dbo.dim_required_document_types
SET
    required_for_applicant = CASE
        WHEN document_code IN ('ACTA_NACIMIENTO') THEN 0
        WHEN document_code IN ('CV', 'NDA', 'ID_INE', 'SCHOOL_PROOF', 'OFFER_LETTER', 'CERTIFICADO') THEN 0
        ELSE required_for_applicant
    END,
    is_active = CASE
        WHEN document_code IN ('CV', 'NDA', 'SCHOOL_PROOF', 'OFFER_LETTER', 'CERTIFICADO') THEN 0
        ELSE is_active
    END
WHERE document_code IN ('ACTA_NACIMIENTO', 'CV', 'NDA', 'ID_INE', 'SCHOOL_PROOF', 'OFFER_LETTER', 'CERTIFICADO');
GO

UPDATE dbo.fact_process_requirements
SET is_required = 0
WHERE process_type_id IN ('PROC_NEW_HIRE', 'PROC_ALTA')
  AND requirement_scope = 'Applicant'
  AND required_document_type_id IN (
      'RDT_CV',
      'RDT_NDA',
      'RDT_ID_INE',
      'RDT_SCHOOL_PROOF',
      'RDT_OFFER_LETTER',
      'RDT_CERTIFICADO',
      'RDT_ACTA_NACIMIENTO'
  );
GO

MERGE dbo.fact_process_requirements AS target
USING (
    VALUES
        ('REQ-P1-ALTA', 'PROC_NEW_HIRE', 'RDT_ALTA', 1, 'Applicant'),
        ('REQ-P1-CURP', 'PROC_NEW_HIRE', 'RDT_CURP', 1, 'Applicant'),
        ('REQ-P1-CONSTANCIA', 'PROC_NEW_HIRE', 'RDT_CONSTANCIA_ESTUDIOS', 1, 'Applicant'),
        ('REQ-P1-IDENTIFICACION', 'PROC_NEW_HIRE', 'RDT_IDENTIFICACION', 1, 'Applicant'),
        ('REQ-P1-DOMICILIO', 'PROC_NEW_HIRE', 'RDT_COMPROBANTE_DOMICILIO', 1, 'Applicant'),
        ('REQ-ALTA-P1-ALTA', 'PROC_ALTA', 'RDT_ALTA', 1, 'Applicant'),
        ('REQ-ALTA-P1-CURP', 'PROC_ALTA', 'RDT_CURP', 1, 'Applicant'),
        ('REQ-ALTA-P1-CONSTANCIA', 'PROC_ALTA', 'RDT_CONSTANCIA_ESTUDIOS', 1, 'Applicant'),
        ('REQ-ALTA-P1-IDENTIFICACION', 'PROC_ALTA', 'RDT_IDENTIFICACION', 1, 'Applicant'),
        ('REQ-ALTA-P1-DOMICILIO', 'PROC_ALTA', 'RDT_COMPROBANTE_DOMICILIO', 1, 'Applicant')
) AS source (
    requirement_id,
    process_type_id,
    required_document_type_id,
    is_required,
    requirement_scope
)
    ON target.requirement_id = source.requirement_id
WHEN MATCHED THEN
    UPDATE SET
        process_type_id = source.process_type_id,
        required_document_type_id = source.required_document_type_id,
        is_required = source.is_required,
        requirement_scope = source.requirement_scope
WHEN NOT MATCHED THEN
    INSERT (
        requirement_id,
        process_type_id,
        required_document_type_id,
        is_required,
        requirement_scope
    )
    VALUES (
        source.requirement_id,
        source.process_type_id,
        source.required_document_type_id,
        source.is_required,
        source.requirement_scope
    );
GO

UPDATE dbo.fact_intern_missing_items
SET
    status = 'Resolved',
    resolved_at = COALESCE(resolved_at, SYSUTCDATETIME()),
    missing_description = CONCAT(missing_description, ' Legacy applicant requirement resolved by Paquete 1 migration.')
WHERE status = 'Open'
  AND missing_type = 'Document'
  AND missing_code IN ('CV', 'NDA', 'ID_INE', 'SCHOOL_PROOF', 'OFFER_LETTER', 'CERTIFICADO', 'ACTA_NACIMIENTO');
GO
