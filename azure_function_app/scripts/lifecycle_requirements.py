import uuid
from datetime import datetime, UTC, timedelta

import pandas as pd


STABLE_IDENTIFIER_FIELDS = [
    "employee_number",
    "cemex_employee_number",
    "email",
    "curp",
    "rfc",
]


def clean_value(value):
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None

    return value


def clean_date(value):
    if pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def normalize_status(value):
    status = clean_value(value)

    if status is None:
        return None

    return (
        str(status)
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def infer_process_type(classification, file_name, canonical_row=None):
    file_name_lower = (file_name or "").lower()
    file_profile_id = (classification or {}).get("file_profile_id")
    classifier_process = (classification or {}).get("process_type_id")
    status = normalize_status((canonical_row or {}).get("status"))

    if any(token in file_name_lower for token in ["baja", "termination"]):
        return "PROC_BAJA"

    if any(token in file_name_lower for token in ["extension", "extendimiento"]):
        return "PROC_EXTENSION"

    if any(token in file_name_lower for token in ["alta"]):
        return "PROC_ALTA"

    if file_profile_id in {"current_interns_excel", "current_interns_csv"}:
        return "PROC_CURRENT_SYNC"

    if file_profile_id == "accepted_hires_excel" or classifier_process == "new_hire":
        return "PROC_NEW_HIRE"

    if file_profile_id == "requisition_excel" or classifier_process == "requisition":
        return "PROC_REQUISITION"

    if status in {"baja", "inactive", "inactivo"}:
        return "PROC_BAJA"

    if status in {"extension pending", "extension pendiente"}:
        return "PROC_EXTENSION"

    if classifier_process == "document_refresh":
        return "PROC_DOCUMENT_REFRESH"

    return "PROC_UNKNOWN"


def get_required_documents_for_process(cursor, process_type_id):
    cursor.execute(
        """
        SELECT
            pr.requirement_id,
            pr.process_type_id,
            pr.required_document_type_id,
            rdt.document_code,
            rdt.document_name,
            rdt.required_for_coparmex,
            rdt.required_for_hr,
            rdt.required_for_applicant,
            pr.is_required,
            pr.requirement_scope
        FROM fact_process_requirements pr
        INNER JOIN dim_required_document_types rdt
            ON pr.required_document_type_id = rdt.required_document_type_id
        WHERE pr.process_type_id = ?
          AND pr.is_required = 1
          AND rdt.is_active = 1
        ORDER BY rdt.document_code
        """,
        process_type_id,
    )

    columns = [column[0] for column in cursor.description]

    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def has_stable_identifier(canonical_row):
    return any(clean_value(canonical_row.get(field)) for field in STABLE_IDENTIFIER_FIELDS)


def missing_item(missing_type, code, description, severity):
    return {
        "missing_type": missing_type,
        "missing_code": code,
        "missing_description": description,
        "severity": severity,
    }


def detect_missing_data_for_row(canonical_row, process_type_id):
    missing_items = []
    start_date = clean_date(canonical_row.get("start_date"))
    end_date = clean_date(canonical_row.get("end_date"))
    status = normalize_status(canonical_row.get("status"))
    today = datetime.now(UTC).date()

    if process_type_id in {"PROC_NEW_HIRE", "PROC_ALTA"}:
        if not (clean_value(canonical_row.get("full_name")) or clean_value(canonical_row.get("first_name"))):
            missing_items.append(missing_item("DataField", "FULL_NAME", "Missing intern full name or first name.", "Error"))

        if not clean_value(canonical_row.get("university")):
            missing_items.append(missing_item("DataField", "UNIVERSITY", "Missing university.", "Error"))

        if not clean_value(canonical_row.get("career")):
            missing_items.append(missing_item("DataField", "CAREER", "Missing career/major.", "Error"))

        if not start_date:
            missing_items.append(missing_item("DataField", "START_DATE", "Missing start date.", "Error"))

        if not end_date:
            missing_items.append(missing_item("DataField", "END_DATE", "Missing end date.", "Error"))

        if not status:
            missing_items.append(missing_item("DataField", "STATUS", "Missing lifecycle/status value.", "Error"))

    if process_type_id == "PROC_CURRENT_SYNC":
        if not has_stable_identifier(canonical_row):
            missing_items.append(missing_item("DataField", "STABLE_IDENTIFIER", "Missing employee number, CEMEX employee number, email, CURP, or RFC.", "Error"))

        if not status:
            missing_items.append(missing_item("DataField", "STATUS", "Missing current intern status.", "Error"))

        if status in {"active", "activo"} and not end_date:
            missing_items.append(missing_item("DataField", "END_DATE", "Active intern is missing end date.", "Error"))

        if not clean_value(canonical_row.get("oi_hc")):
            missing_items.append(missing_item("BusinessRule", "OI_HC", "Missing OI HC.", "Warning"))

        if not clean_value(canonical_row.get("cc_hc")):
            missing_items.append(missing_item("BusinessRule", "CC_HC", "Missing CC HC.", "Warning"))

    if process_type_id == "PROC_EXTENSION":
        if not has_stable_identifier(canonical_row):
            missing_items.append(missing_item("DataField", "STABLE_IDENTIFIER", "Extension requires a stable intern identifier.", "Error"))

        if not end_date:
            missing_items.append(missing_item("DataField", "END_DATE", "Extension requires updated end date.", "Error"))

        if not status:
            missing_items.append(missing_item("DataField", "STATUS", "Extension requires status.", "Error"))

    if process_type_id == "PROC_BAJA":
        if not has_stable_identifier(canonical_row):
            missing_items.append(missing_item("DataField", "STABLE_IDENTIFIER", "Baja requires a stable intern identifier.", "Error"))

        if not status:
            missing_items.append(missing_item("DataField", "STATUS", "Baja requires status.", "Error"))

    if start_date and end_date and start_date > end_date:
        missing_items.append(missing_item("Validation", "DATE_ORDER", "Start date is after end date.", "Error"))

    if status in {"active", "activo"} and end_date:
        if end_date < today:
            missing_items.append(missing_item("Validation", "EXPIRED_ACTIVE_END_DATE", "Active intern has an expired end date.", "Warning"))

        if today <= end_date <= today + timedelta(days=30):
            missing_items.append(missing_item("Validation", "UPCOMING_EXPIRATION", "Intern end date is within 30 days.", "Warning"))

    return missing_items


def detect_missing_documents_for_intern(cursor, intern_id, process_type_id):
    if not intern_id:
        return []

    required_documents = get_required_documents_for_process(cursor, process_type_id)
    missing_documents = []

    for document in required_documents:
        document_code = document["document_code"]

        cursor.execute(
            """
            SELECT TOP 1 intern_document_status_id
            FROM fact_intern_document_status
            WHERE intern_id = ?
              AND (
                  document_type_id = ?
                  OR document_type_id = ?
              )
              AND status IN ('Stored', 'Validated', 'Received')
            ORDER BY created_at DESC
            """,
            intern_id,
            document["required_document_type_id"],
            document_code,
        )

        if cursor.fetchone():
            continue

        missing_documents.append(missing_item(
            "Document",
            document_code,
            f"Missing required document: {document['document_name']}.",
            "Error",
        ))

    return missing_documents


def log_missing_item(
    cursor,
    intern_id,
    process_type_id,
    missing_type,
    missing_code,
    missing_description,
    severity,
    source_file_id=None
):
    cursor.execute(
        """
        SELECT TOP 1 missing_item_id
        FROM fact_intern_missing_items
        WHERE ISNULL(intern_id, '') = ISNULL(?, '')
          AND ISNULL(process_type_id, '') = ISNULL(?, '')
          AND missing_code = ?
          AND status = 'Open'
        """,
        intern_id,
        process_type_id,
        missing_code,
    )

    existing = cursor.fetchone()

    if existing:
        return existing[0]

    missing_item_id = "MISS-" + str(uuid.uuid4())[:8]

    cursor.execute(
        """
        INSERT INTO fact_intern_missing_items (
            missing_item_id,
            intern_id,
            process_type_id,
            missing_type,
            missing_code,
            missing_description,
            severity,
            status,
            source_file_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?)
        """,
        missing_item_id,
        intern_id,
        process_type_id,
        missing_type,
        missing_code,
        missing_description,
        severity,
        source_file_id,
    )

    return missing_item_id


def resolve_missing_item(cursor, intern_id, missing_code):
    cursor.execute(
        """
        UPDATE fact_intern_missing_items
        SET
            status = 'Resolved',
            resolved_at = SYSUTCDATETIME()
        WHERE ISNULL(intern_id, '') = ISNULL(?, '')
          AND missing_code = ?
          AND status = 'Open'
        """,
        intern_id,
        missing_code,
    )


def log_lifecycle_event(
    cursor,
    intern_id,
    process_type_id,
    event_type,
    event_description,
    source_file_id=None,
    old_status=None,
    new_status=None,
    run_id=None,
    source_row_number=None,
    event_status="Observed",
    needs_review=0,
):
    lifecycle_event_id = "LCE-" + str(uuid.uuid4())[:8]

    cursor.execute(
        """
        INSERT INTO fact_intern_lifecycle_events (
            lifecycle_event_id,
            run_id,
            file_id,
            intern_id,
            process_type_id,
            event_type,
            event_status,
            source_row_number,
            old_status,
            new_status,
            message,
            needs_review
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lifecycle_event_id,
        run_id,
        source_file_id,
        intern_id,
        process_type_id,
        event_type,
        event_status,
        source_row_number,
        old_status,
        new_status,
        event_description,
        needs_review,
    )

    return lifecycle_event_id
