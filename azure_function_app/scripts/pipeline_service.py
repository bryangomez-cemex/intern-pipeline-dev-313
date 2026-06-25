import os
import sys
import uuid
import mimetypes
import re
import unicodedata
from datetime import datetime, UTC, timedelta

import pandas as pd
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import flexible_file_classifier
import lifecycle_requirements
import communication_packager
from app_config import CONFIG
import azure_clients


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = CONFIG.azure_storage_connection_string
RAW_UPLOADS_CONTAINER = CONFIG.raw_uploads_container
ERROR_REPORTS_CONTAINER = CONFIG.error_reports_container
ARCHIVE_CONTAINER = CONFIG.archive_container

SQL_SERVER = CONFIG.azure_sql_server
SQL_DATABASE = CONFIG.azure_sql_database
PIPELINE_RUN_TYPE = os.getenv("PIPELINE_RUN_TYPE", "manual")
LOCAL_WORK_DIR = CONFIG.local_work_dir


# ============================================================
# SQL CONNECTION USING MICROSOFT ENTRA TOKEN
# ============================================================

def get_sql_connection():
    return azure_clients.get_sql_connection()


# ============================================================
# GENERAL HELPERS
# ============================================================

def utc_now_iso():
    return datetime.now(UTC).isoformat()


def utc_timestamp():
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


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


def clean_org_value(value):
    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    if isinstance(value, int):
        return str(value)

    text = str(value).strip()

    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]

    return text or None


def org_key(value):
    value = clean_org_value(value)

    if value is None:
        return None

    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))

    return " ".join(normalized.lower().split())


def org_value_variants(value):
    value = clean_org_value(value)

    if value is None:
        return []

    variants = {value, str(value).strip()}

    if re.fullmatch(r"\d+", value):
        variants.add(f"{value}.0")

    if re.fullmatch(r"\d+\.0", value):
        variants.add(value[:-2])

    return sorted({org_key(variant) for variant in variants if org_key(variant)})


def manager_key(value):
    return org_key(value)


def clean_date(value):
    if pd.isna(value):
        return None

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def normalize_column_name(col):
    if col is None:
        return ""

    return (
        str(col)
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
        .strip()
    )


def get_file_type_id(extension: str):
    extension = extension.lower().replace(".", "")

    mapping = {
        "pdf": "FT001",
        "xlsx": "FT002",
        "csv": "FT003",
        "png": "FT004",
        "jpg": "FT005",
        "jpeg": "FT006",
    }

    return mapping.get(extension)


def get_document_type_id(file_name: str, extension: str):
    name = file_name.lower()

    if extension in ["xlsx", "csv"]:
        return "DOC004"

    if "cv" in name or "resume" in name or "curriculum" in name:
        return "DOC006"

    if "nda" in name or "confidencial" in name:
        return "DOC007"

    if "acta" in name or "nacimiento" in name:
        return "DOC008"

    if "offer" in name or "oferta" in name:
        return "DOC009"

    if "forms" in name or "onboarding" in name:
        return "DOC010"

    if "convenio" in name:
        return "DOC001"

    if "identificacion" in name or "ine" in name or "id" in name:
        return "DOC002"

    if "comprobante" in name or "escolar" in name or "universidad" in name:
        return "DOC003"

    if "coparmex" in name:
        return "DOC005"

    return "DOC999"


def generate_file_id():
    return "FILE-" + str(uuid.uuid4())[:8]


def generate_validation_id():
    return "VAL-" + str(uuid.uuid4())[:8]


def generate_status_history_id():
    return "SH-" + str(uuid.uuid4())[:8]


def generate_communication_id():
    return "COMM-" + str(uuid.uuid4())[:8]


def generate_run_id():
    return "RUN-" + str(uuid.uuid4())[:8]


def generate_processed_blob_id():
    return "PB-" + str(uuid.uuid4())[:8]


def generate_classification_id():
    return "CLS-" + str(uuid.uuid4())[:8]


def generate_detected_column_id():
    return "DCOL-" + str(uuid.uuid4())[:8]


def generate_intern_document_status_id():
    return "IDS-" + str(uuid.uuid4())[:8]


def generate_lifecycle_event_id():
    return "LCE-" + str(uuid.uuid4())[:8]


class SelectedBlob:
    def __init__(self, name, properties):
        self.name = name
        self.size = getattr(properties, "size", None)
        self.last_modified = getattr(properties, "last_modified", None)
        self.etag = getattr(properties, "etag", None)


def generate_intern_id(row):
    num_empleado = clean_value(row.get("NumEmpleado"))
    num_empleado_cemex = clean_value(row.get("NumEmpleadoCemex"))
    curp = clean_value(row.get("CURP"))

    if num_empleado:
        return f"INT-{str(num_empleado)}"

    if num_empleado_cemex:
        return f"INT-CEMEX-{str(num_empleado_cemex)}"

    if curp:
        return f"INT-CURP-{str(curp)}"

    return "INT-" + str(uuid.uuid4())[:8]


# ============================================================
# BLOB STORAGE HELPERS
# ============================================================

def get_blob_service_client():
    return azure_clients.get_blob_service_client()


def upload_file_to_blob(container_name, local_path, blob_name):
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(container_name)

    with open(local_path, "rb") as file_data:
        container_client.upload_blob(
            name=blob_name,
            data=file_data,
            overwrite=True
        )

    return blob_name


def sanitize_blob_path(blob_name):
    raw_parts = str(blob_name or "").replace("\\", "/").split("/")
    safe_parts = []

    for raw_part in raw_parts:
        part = raw_part.strip()

        if not part or part in {".", ".."}:
            continue

        safe_part = re.sub(r"[^A-Za-z0-9._ -]", "_", part).strip(" .")

        if not safe_part:
            safe_part = "unnamed"

        safe_parts.append(safe_part)

    return "/".join(safe_parts) or f"uploaded_{utc_timestamp()}"


def timestamp_archive_blob_name(archive_blob_name):
    folder, _, file_name = archive_blob_name.rpartition("/")
    stem, extension = os.path.splitext(file_name or archive_blob_name)
    timestamped_file_name = f"{stem}_{utc_timestamp()}_{str(uuid.uuid4())[:8]}{extension}"

    if folder:
        return f"{folder}/{timestamped_file_name}"

    return timestamped_file_name


def archive_processed_blob(source_container_name, source_blob_name, success=True):
    """
    Copies a processed blob into the archive container and deletes the original
    only after the archive upload succeeds.

    success=True  -> archive/processed/...
    success=False -> archive/failed/...
    """
    blob_service_client = get_blob_service_client()

    source_blob_client = blob_service_client.get_blob_client(
        container=source_container_name,
        blob=source_blob_name
    )

    archive_container_client = blob_service_client.get_container_client(
        ARCHIVE_CONTAINER
    )

    status_folder = "processed" if success else "failed"

    sanitized_source_blob_name = sanitize_blob_path(source_blob_name)
    archived_blob_name = f"{status_folder}/{sanitized_source_blob_name}"

    archive_blob_client = archive_container_client.get_blob_client(
        archived_blob_name
    )

    if archive_blob_client.exists():
        archived_blob_name = timestamp_archive_blob_name(archived_blob_name)
        archive_blob_client = archive_container_client.get_blob_client(
            archived_blob_name
        )

    print(f"Archive original blob: {source_container_name}/{source_blob_name}")
    print(f"Archive validation result: {'Validation Passed' if success else 'Validation Failed'}")
    print(f"Archive destination: {ARCHIVE_CONTAINER}/{archived_blob_name}")

    source_blob_data = source_blob_client.download_blob().readall()
    archive_blob_client.upload_blob(source_blob_data, overwrite=False)

    archive_properties = archive_blob_client.get_blob_properties()

    if archive_properties.size != len(source_blob_data):
        raise RuntimeError(
            "Archive upload size mismatch. "
            f"Expected {len(source_blob_data)} bytes, got {archive_properties.size}."
        )

    source_blob_client.delete_blob()
    print("Archive source deleted from raw container: True")

    return archived_blob_name


# ============================================================
# SQL INSERT / UPDATE FUNCTIONS
# ============================================================

def insert_fact_file(
    cursor,
    file_id,
    file_name,
    extension,
    mime_type,
    size_bytes,
    file_type_id,
    document_type_id,
    blob_container,
    blob_path,
    file_status_id="FS004",
    validation_status="Validation In Progress",
    error_message=None,
    send_to_hr=0,
    send_to_coparmex=0
):
    cursor.execute(
        """
        INSERT INTO fact_files (
            file_id,
            document_type_id,
            file_type_id,
            file_status_id,
            original_file_name,
            stored_file_name,
            file_extension,
            mime_type,
            file_size_bytes,
            blob_container,
            blob_path,
            uploaded_by_email,
            received_from_email,
            validation_status,
            error_message,
            send_to_hr,
            send_to_coparmex
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        file_id,
        document_type_id,
        file_type_id,
        file_status_id,
        file_name,
        file_name,
        extension,
        mime_type,
        size_bytes,
        blob_container,
        blob_path,
        "dev.user@example.com",
        "dev.user@example.com",
        validation_status,
        error_message,
        send_to_hr,
        send_to_coparmex,
    )


def update_file_status(cursor, file_id, file_status_id, validation_status, error_message=None):
    cursor.execute(
        """
        UPDATE fact_files
        SET file_status_id = ?,
            validation_status = ?,
            error_message = ?
        WHERE file_id = ?
        """,
        file_status_id,
        validation_status,
        error_message,
        file_id,
    )


def update_file_archive_location(cursor, file_id, archived_blob_name):
    cursor.execute(
        """
        UPDATE fact_files
        SET
            blob_container = ?,
            blob_path = ?,
            stored_file_name = ?
        WHERE file_id = ?
        """,
        ARCHIVE_CONTAINER,
        archived_blob_name,
        os.path.basename(archived_blob_name),
        file_id,
    )


def insert_validation(
    cursor,
    file_id,
    rule_id,
    field_name,
    validation_type,
    severity,
    result,
    error_message=None,
    suggested_fix=None,
    intern_id=None
):
    validation_id = generate_validation_id()

    cursor.execute(
        """
        INSERT INTO fact_validations (
            validation_id,
            intern_id,
            file_id,
            validation_rule_id,
            field_name,
            validation_type,
            severity,
            validation_result,
            error_message,
            suggested_fix
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        validation_id,
        intern_id,
        file_id,
        rule_id,
        field_name,
        validation_type,
        severity,
        result,
        error_message,
        suggested_fix,
    )


def insert_status_history(
    cursor,
    entity_type,
    entity_id,
    old_status_id,
    new_status_id,
    changed_by="pipeline",
    change_reason=None
):
    status_history_id = generate_status_history_id()

    cursor.execute(
        """
        INSERT INTO fact_status_history (
            status_history_id,
            entity_type,
            entity_id,
            old_status_id,
            new_status_id,
            changed_by,
            change_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        status_history_id,
        entity_type,
        entity_id,
        old_status_id,
        new_status_id,
        changed_by,
        change_reason,
    )


def insert_pipeline_run(
    cursor,
    run_id,
    run_type,
    source_script,
    status,
    source_container=None,
    source_blob_name=None
):
    cursor.execute(
        """
        INSERT INTO fact_pipeline_runs (
            run_id,
            run_type,
            source_script,
            status,
            source_container,
            source_blob_name
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        run_id,
        run_type,
        source_script,
        status,
        source_container,
        source_blob_name,
    )


def update_pipeline_run_source(cursor, run_id, source_container, source_blob_name):
    cursor.execute(
        """
        UPDATE fact_pipeline_runs
        SET
            source_container = ?,
            source_blob_name = ?
        WHERE run_id = ?
        """,
        source_container,
        source_blob_name,
        run_id,
    )


def finish_pipeline_run(
    cursor,
    run_id,
    status,
    archived_blob_name=None,
    source_file_id=None,
    error_report_file_id=None,
    communication_id=None,
    good_rows=None,
    bad_rows=None,
    total_rows=None,
    error_message=None
):
    cursor.execute(
        """
        UPDATE fact_pipeline_runs
        SET
            finished_at = SYSUTCDATETIME(),
            status = ?,
            archived_blob_name = COALESCE(?, archived_blob_name),
            source_file_id = COALESCE(?, source_file_id),
            error_report_file_id = COALESCE(?, error_report_file_id),
            communication_id = COALESCE(?, communication_id),
            good_rows = COALESCE(?, good_rows),
            bad_rows = COALESCE(?, bad_rows),
            total_rows = COALESCE(?, total_rows),
            error_message = ?
        WHERE run_id = ?
        """,
        status,
        archived_blob_name,
        source_file_id,
        error_report_file_id,
        communication_id,
        good_rows,
        bad_rows,
        total_rows,
        error_message,
        run_id,
    )


def processed_blob_exists(cursor, source_container, source_blob_name):
    cursor.execute(
        """
        SELECT TOP 1 processed_blob_id
        FROM fact_processed_blobs
        WHERE source_container = ?
          AND source_blob_name = ?
        """,
        source_container,
        source_blob_name,
    )

    return cursor.fetchone() is not None


def sql_datetime_from_blob_datetime(value):
    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)

    return value


def insert_processed_blob(
    cursor,
    source_container,
    source_blob_name,
    source_blob_size_bytes,
    source_blob_last_modified,
    source_blob_etag,
    source_file_id,
    run_id,
    archived_blob_name,
    status
):
    processed_blob_id = generate_processed_blob_id()

    cursor.execute(
        """
        INSERT INTO fact_processed_blobs (
            processed_blob_id,
            source_container,
            source_blob_name,
            source_blob_size_bytes,
            source_blob_last_modified,
            source_blob_etag,
            source_file_id,
            run_id,
            archived_blob_name,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        processed_blob_id,
        source_container,
        source_blob_name,
        source_blob_size_bytes,
        sql_datetime_from_blob_datetime(source_blob_last_modified),
        source_blob_etag,
        source_file_id,
        run_id,
        archived_blob_name,
        status,
    )

    return processed_blob_id


def insert_file_classification(cursor, classification):
    classification_id = generate_classification_id()

    cursor.execute(
        """
        INSERT INTO fact_file_classification (
            classification_id,
            run_id,
            file_id,
            source_container,
            source_blob_name,
            file_name,
            file_extension,
            mime_type,
            sheet_names,
            detected_column_count,
            detected_file_profile_id,
            detected_document_type_id,
            detected_process_type_id,
            classification_confidence,
            classification_reason,
            needs_review
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        classification_id,
        classification.get("run_id"),
        classification.get("file_id"),
        classification.get("source_container"),
        classification.get("source_blob_name"),
        classification.get("file_name"),
        classification.get("file_extension"),
        classification.get("mime_type"),
        classification.get("sheet_names"),
        classification.get("detected_column_count"),
        classification.get("file_profile_id"),
        classification.get("document_type_id"),
        classification.get("process_type_id"),
        classification.get("classification_confidence"),
        classification.get("classification_reason"),
        1 if classification.get("needs_review") else 0,
    )

    return classification_id


def insert_detected_column(cursor, run_id, file_id, source_container, source_blob_name, column_info):
    detected_column_id = generate_detected_column_id()

    cursor.execute(
        """
        INSERT INTO fact_detected_columns (
            detected_column_id,
            run_id,
            file_id,
            source_container,
            source_blob_name,
            sheet_name,
            ordinal_position,
            source_column_name,
            normalized_column_name,
            canonical_field_id,
            canonical_field_name,
            source_profile,
            mapping_confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        detected_column_id,
        run_id,
        file_id,
        source_container,
        source_blob_name,
        column_info.get("sheet_name"),
        column_info.get("ordinal_position"),
        column_info.get("source_column_name"),
        column_info.get("normalized_column_name"),
        column_info.get("canonical_field_id"),
        column_info.get("canonical_field_name"),
        column_info.get("source_profile"),
        column_info.get("mapping_confidence"),
    )

    return detected_column_id


def insert_intern_document_status(
    cursor,
    intern_id,
    process_type_id,
    document_type_id,
    file_id,
    status,
    validation_status,
    is_required=0,
    is_missing=0,
    is_expired=0,
    notes=None
):
    intern_document_status_id = generate_intern_document_status_id()

    cursor.execute(
        """
        INSERT INTO fact_intern_document_status (
            intern_document_status_id,
            intern_id,
            process_type_id,
            document_type_id,
            file_id,
            status,
            validation_status,
            is_required,
            is_missing,
            is_expired,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        intern_document_status_id,
        intern_id,
        process_type_id,
        document_type_id,
        file_id,
        status,
        validation_status,
        is_required,
        is_missing,
        is_expired,
        notes,
    )

    return intern_document_status_id


def insert_lifecycle_event(
    cursor,
    run_id,
    file_id,
    intern_id,
    process_type_id,
    event_type,
    event_status,
    source_row_number=None,
    old_status=None,
    new_status=None,
    message=None,
    needs_review=0
):
    lifecycle_event_id = generate_lifecycle_event_id()

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
        file_id,
        intern_id,
        process_type_id,
        event_type,
        event_status,
        source_row_number,
        old_status,
        new_status,
        message,
        needs_review,
    )

    return lifecycle_event_id


def insert_communication(
    cursor,
    intern_id,
    requisition_id,
    file_id,
    email_template_id,
    communication_type,
    recipient_group,
    recipient_email,
    subject,
    body,
    status="Prepared",
    error_message=None
):
    communication_id = generate_communication_id()

    cursor.execute(
        """
        INSERT INTO fact_communications (
            communication_id,
            email_type,
            sent_to,
            status,
            file_id,
            email_template_id,
            communication_type,
            recipient_group,
            recipient_email,
            subject,
            body,
            communication_status,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        communication_id,
        communication_type,
        recipient_email,
        status,
        file_id,
        email_template_id,
        communication_type,
        recipient_group,
        recipient_email,
        subject,
        body,
        status,
        error_message,
    )

    return communication_id


# ============================================================
# COMMUNICATION PREPARATION
# ============================================================

def resolve_group_recipients(cursor, recipient_group, fallback):
    """
    Resolve the active recipient email(s) for a fixed group (HR, Coparmex, ...)
    from dim_email_recipients, joined by ';'. Falls back to the provided default
    if the table has no active entry, so the pipeline keeps working safely until
    the table is populated with real addresses.
    """
    try:
        cursor.execute(
            """
            SELECT email
            FROM dim_email_recipients
            WHERE recipient_group = ?
              AND active_flag = 1
              AND email IS NOT NULL
            ORDER BY recipient_id
            """,
            recipient_group,
        )
        emails = [row[0].strip() for row in cursor.fetchall() if row[0] and row[0].strip()]
        if emails:
            return ";".join(emails)
    except Exception as resolve_error:
        print(f"Recipient resolution failed for group {recipient_group}; using fallback. {resolve_error}")

    return fallback


def resolve_applicant_recipient(intern_email=None):
    """
    Applicant-facing email. Uses the intern's own email when available, otherwise
    a single configurable inbox via DEV_EMAIL_OVERRIDE (e.g. an HR intake mailbox),
    otherwise the safe dev placeholder. Per-applicant routing for batch files is a
    future enhancement.
    """
    if intern_email and str(intern_email).strip():
        return str(intern_email).strip()
    return os.getenv("DEV_EMAIL_OVERRIDE") or "dev.intern@example.com"


def prepare_correction_communication(
    cursor,
    source_file_id,
    source_file_name,
    error_report_file_id,
    error_report_name,
    error_count
):
    subject = f"Correction needed: {source_file_name}"

    body = (
        f"The uploaded file {source_file_name} has {error_count} validation errors.\n\n"
        f"An error report was generated: {error_report_name}\n\n"
        "Please review the report, correct the file, and upload the corrected version.\n\n"
        "This is a prepared communication record. No real email has been sent yet."
    )

    return insert_communication(
        cursor=cursor,
        intern_id=None,
        requisition_id=None,
        file_id=error_report_file_id,
        email_template_id="ET005",
        communication_type="Correction Needed",
        recipient_group="Intern / Applicant",
        recipient_email=resolve_applicant_recipient(),
        subject=subject,
        body=body,
        status="Prepared",
        error_message=None
    )


def prepare_hr_package_communication(
    cursor,
    source_file_id,
    source_file_name,
    good_rows
):
    subject = f"HR package ready: {source_file_name}"

    body = (
        f"The uploaded file {source_file_name} passed validation.\n\n"
        f"{good_rows} intern records were inserted or updated.\n\n"
        "This package is ready for HR review.\n\n"
        "This is a prepared communication record. No real email has been sent yet."
    )

    return insert_communication(
        cursor=cursor,
        intern_id=None,
        requisition_id=None,
        file_id=source_file_id,
        email_template_id="ET002",
        communication_type="HR Complete Package",
        recipient_group="HR",
        recipient_email=resolve_group_recipients(cursor, "HR", "dev.hr@example.com"),
        subject=subject,
        body=body,
        status="Prepared",
        error_message=None
    )


def prepare_coparmex_package_communication(
    cursor,
    source_file_id,
    source_file_name
):
    subject = f"Coparmex package ready: {source_file_name}"

    body = (
        f"The required Coparmex package for {source_file_name} is ready.\n\n"
        "Only Coparmex-approved files should be included in the real email step.\n\n"
        "This is a prepared communication record. No real email has been sent yet."
    )

    return insert_communication(
        cursor=cursor,
        intern_id=None,
        requisition_id=None,
        file_id=source_file_id,
        email_template_id="ET003",
        communication_type="Coparmex Package",
        recipient_group="Coparmex",
        recipient_email=resolve_group_recipients(cursor, "Coparmex", "dev.coparmex@example.com"),
        subject=subject,
        body=body,
        status="Prepared",
        error_message=None
    )


def prepare_intern_confirmation_communication(
    cursor,
    source_file_id,
    source_file_name,
    good_rows
):
    subject = f"File processed: {source_file_name}"

    body = (
        f"The uploaded file {source_file_name} was processed successfully.\n\n"
        f"{good_rows} records were accepted.\n\n"
        "The HR team will contact the intern/applicant if anything else is needed.\n\n"
        "This is a prepared communication record. No real email has been sent yet."
    )

    return insert_communication(
        cursor=cursor,
        intern_id=None,
        requisition_id=None,
        file_id=source_file_id,
        email_template_id="ET004",
        communication_type="Intern Confirmation",
        recipient_group="Intern / Applicant",
        recipient_email=resolve_applicant_recipient(),
        subject=subject,
        body=body,
        status="Prepared",
        error_message=None
    )


# ============================================================
# EXCEL VALIDATION
# ============================================================

def get_required_columns():
    return [
        "NumEmpleado",
        "NumEmpleadoCemex",
        "NSS",
        "RFC",
        "CURP",
        "Nombre",
        "Paterno",
        "Materno",
        "NombreCompleto",
        "Puesto",
        "ConceptID",
        "Concepto",
        "RAZON SOCIAL HC",
        "RazonSocial",
        "FechadeIngreso",
        "FechaContratoVence",
        "JefeInmediato",
        "UBICACIÓN HC",
        "ESTADO UBICACIÓN HC",
        "ASESOR RRHH HC",
        "SalarioMensual",
        "CC HC",
        "VP HC",
        "RegionRH",
        "OI HC",
        "ElementoPep",
        "Grafo",
        "NoOperacion",
        "Cuenta",
        "Sublibro",
        "DiasFacturados",
        "Seguro",
        "ClasedeRiesgo",
        "FrecuenciaPago",
        "ImporteSinComision",
        "Comision",
        "Importe",
        "ImporteTotal",
        "Notas",
        "Estatus",
        "CIA HC",
        "Sexo",
        "Edad",
        "Universidad",
        "Carrera",
        "Semestre",
        "Area",
    ]


def validate_excel_columns(local_path):
    required_columns = get_required_columns()

    df = pd.read_excel(local_path)
    df.columns = [normalize_column_name(col) for col in df.columns]
    df = df.dropna(how="all")

    print("Columns found in Excel:")
    for col in df.columns:
        print(f"- {col}")

    missing_columns = [col for col in required_columns if col not in df.columns]

    return df, missing_columns


def validate_intern_row(row):
    errors = []

    nombre_completo = clean_value(row.get("NombreCompleto"))
    oi_hc = clean_value(row.get("OI HC"))
    cc_hc = clean_value(row.get("CC HC"))
    manager = clean_value(row.get("JefeInmediato"))
    company = clean_value(row.get("CIA HC")) or clean_value(row.get("RazonSocial")) or clean_value(row.get("RAZON SOCIAL HC"))
    vp_hc = clean_value(row.get("VP HC"))
    salary = clean_value(row.get("SalarioMensual"))
    universidad = clean_value(row.get("Universidad"))
    estatus = clean_value(row.get("Estatus"))

    fecha_ingreso = clean_date(row.get("FechadeIngreso"))
    fecha_vence = clean_date(row.get("FechaContratoVence"))

    if not nombre_completo:
        errors.append((
            "VR001",
            "NombreCompleto",
            "Missing full name",
            "Add the intern full name."
        ))

    if not oi_hc:
        errors.append((
            "VR009",
            "OI HC",
            "Missing OI HC",
            "Add the correct internal order."
        ))

    if not cc_hc:
        errors.append((
            "VR010",
            "CC HC",
            "Missing CC HC",
            "Add the correct cost center."
        ))

    if not manager:
        errors.append((
            "VR011",
            "JefeInmediato",
            "Missing manager",
            "Add the intern manager or jefe inmediato."
        ))

    if not company:
        errors.append((
            "VR012",
            "CIA HC",
            "Missing company",
            "Add the intern company/compania."
        ))

    if not vp_hc:
        errors.append((
            "VR013",
            "VP HC",
            "Missing VP",
            "Add the VP responsible for the intern."
        ))

    if salary is not None:
        try:
            salary_value = float(salary)
            if salary_value < 0 or salary_value > 100000:
                errors.append((
                    "VR014",
                    "SalarioMensual",
                    "Salary is outside the expected fake-data range",
                    "Review the monthly salary amount."
                ))
        except (TypeError, ValueError):
            errors.append((
                "VR014",
                "SalarioMensual",
                "Salary is not numeric",
                "Use a numeric monthly salary amount."
            ))

    if fecha_ingreso and fecha_vence and fecha_ingreso > fecha_vence:
        errors.append((
            "VR005",
            "FechaContratoVence",
            "Contract end date is before start date",
            "Review FechadeIngreso and FechaContratoVence."
        ))

    if not universidad:
        errors.append((
            "VR015",
            "Universidad",
            "Missing university",
            "Add the intern university."
        ))

    if not estatus:
        errors.append((
            "VR001",
            "Estatus",
            "Missing status",
            "Add the intern status."
        ))

    return errors


def has_stable_identifier(row):
    stable_fields = [
        "NumEmpleado",
        "NumEmpleadoCemex",
        "CURP",
        "RFC",
        "NSS",
    ]

    return any(clean_value(row.get(field_name)) for field_name in stable_fields)


def is_non_intern_summary_row(row, process_type_id):
    if process_type_id not in {"current_intern_sync", "PROC_CURRENT_SYNC"}:
        return False

    if has_stable_identifier(row):
        return False

    return not any(
        clean_value(row.get(field_name))
        for field_name in ("NombreCompleto", "Nombre", "Paterno", "Materno", "Estatus")
    )


def validate_flexible_intern_row(row, process_type_id):
    if process_type_id in {"current_intern_sync", "PROC_CURRENT_SYNC"}:
        errors = []

        if not has_stable_identifier(row):
            errors.append((
                "VR020",
                "stable_identifier",
                "No reliable identifier found for current intern row",
                "Add employee number, CEMEX employee number, CURP, RFC, or NSS."
            ))

        if not clean_value(row.get("NombreCompleto")):
            errors.append((
                "VR001",
                "NombreCompleto",
                "Missing full name",
                "Add the intern full name."
            ))

        return errors

    errors = validate_intern_row(row)

    return errors


# ============================================================
# ERROR REPORT GENERATION
# ============================================================

def create_error_report(error_rows, source_file_id):
    if not error_rows:
        return None, None, 0

    error_reports_dir = os.path.join(LOCAL_WORK_DIR, "error_reports")
    os.makedirs(error_reports_dir, exist_ok=True)

    timestamp = utc_timestamp()
    report_file_name = f"error_report_{source_file_id}_{timestamp}.xlsx"
    local_path = os.path.join(error_reports_dir, report_file_name)

    report_df = pd.DataFrame(error_rows)

    with pd.ExcelWriter(local_path, engine="openpyxl") as writer:
        report_df.to_excel(writer, index=False, sheet_name="Validation Errors")

    return local_path, report_file_name, len(report_df)


def log_error_report_file(cursor, report_file_id, report_file_name, report_blob_path, report_size_bytes):
    insert_fact_file(
        cursor=cursor,
        file_id=report_file_id,
        file_name=report_file_name,
        extension="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=report_size_bytes,
        file_type_id="FT002",
        document_type_id="DOC999",
        blob_container=ERROR_REPORTS_CONTAINER,
        blob_path=report_blob_path,
        file_status_id="FS010",
        validation_status="Archived",
        error_message=None,
        send_to_hr=1,
        send_to_coparmex=0
    )


# ============================================================
# CEMEX ORG RELATION ENRICHMENT
# ============================================================

ORG_FIELD_TO_DB_COLUMN = {
    "JefeInmediato": "jefe_inmediato",
    "VP HC": "vp_hc",
    "CC HC": "cc_hc",
    "OI HC": "oi_hc",
    "CIA HC": "cia_hc",
}

ORG_RELATION_RULES = [
    ("JefeInmediato", "VP HC", 100),
    ("JefeInmediato", "CC HC", 100),
    ("JefeInmediato", "OI HC", 100),
    ("JefeInmediato", "CIA HC", 100),
    ("OI HC", "VP HC", 90),
    ("OI HC", "CC HC", 90),
    ("OI HC", "CIA HC", 85),
    ("CC HC", "VP HC", 80),
    ("CC HC", "CIA HC", 80),
    ("VP HC", "CIA HC", 70),
    ("OI HC", "JefeInmediato", 60),
    ("CC HC", "JefeInmediato", 50),
]

MANAGER_ASSIGNMENT_TARGETS = {
    "VP HC": "vp",
    "CC HC": "cc",
    "OI HC": "oi",
    "CIA HC": "compania",
}


def ensure_manager_assignments_table(cursor):
    cursor.execute(
        """
        IF OBJECT_ID('dbo.dim_manager_assignments','U') IS NULL
        CREATE TABLE dbo.dim_manager_assignments (
          jefe_key NVARCHAR(300) NOT NULL PRIMARY KEY,
          jefe_directo NVARCHAR(200) NULL,
          vp NVARCHAR(200) NULL,
          asesor_rh NVARCHAR(200) NULL,
          ubicacion_udn NVARCHAR(200) NULL,
          estado NVARCHAR(100) NULL,
          compania NVARCHAR(200) NULL,
          oi NVARCHAR(50) NULL,
          cc NVARCHAR(50) NULL,
          updated_at DATETIME2 DEFAULT SYSUTCDATETIME()
        )
        """
    )


def best_unique_candidate(candidates):
    scores = {}
    labels = {}

    for value, count, strength in candidates:
        value = clean_org_value(value)

        if value is None:
            continue

        key = org_key(value)
        score = (strength * 100000) + int(count or 1)
        scores[key] = scores.get(key, 0) + score
        labels.setdefault(key, value)

    if not scores:
        return None

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None

    return labels[ranked[0][0]]


def query_dim_intern_relation(cursor, source_field, source_value, target_field, strength):
    source_column = ORG_FIELD_TO_DB_COLUMN[source_field]
    target_column = ORG_FIELD_TO_DB_COLUMN[target_field]
    variants = org_value_variants(source_value)

    if not variants:
        return []

    placeholders = ", ".join("?" for _ in variants)
    cursor.execute(
        f"""
        SELECT CAST({target_column} AS NVARCHAR(4000)) AS target_value,
               COUNT(*) AS match_count
        FROM dbo.dim_interns
        WHERE {target_column} IS NOT NULL
          AND LTRIM(RTRIM(CAST({target_column} AS NVARCHAR(4000)))) <> ''
          AND LOWER(LTRIM(RTRIM(CAST({source_column} AS NVARCHAR(4000))))) IN ({placeholders})
        GROUP BY CAST({target_column} AS NVARCHAR(4000))
        """,
        *variants,
    )

    return [(row[0], row[1], strength) for row in cursor.fetchall()]


def query_manager_assignment_relation(cursor, source_field, source_value, target_field, strength):
    if source_field != "JefeInmediato" or target_field not in MANAGER_ASSIGNMENT_TARGETS:
        return []

    target_column = MANAGER_ASSIGNMENT_TARGETS[target_field]
    key = manager_key(source_value)
    variants = org_value_variants(source_value)

    if not key and not variants:
        return []

    clauses = []
    params = []

    if key:
        clauses.append("jefe_key = ?")
        params.append(key)

    if variants:
        placeholders = ", ".join("?" for _ in variants)
        clauses.append(f"LOWER(LTRIM(RTRIM(CAST(jefe_directo AS NVARCHAR(4000))))) IN ({placeholders})")
        params.extend(variants)

    cursor.execute(
        f"""
        SELECT CAST({target_column} AS NVARCHAR(4000)) AS target_value,
               COUNT(*) AS match_count
        FROM dbo.dim_manager_assignments
        WHERE {target_column} IS NOT NULL
          AND LTRIM(RTRIM(CAST({target_column} AS NVARCHAR(4000)))) <> ''
          AND ({" OR ".join(clauses)})
        GROUP BY CAST({target_column} AS NVARCHAR(4000))
        """,
        *params,
    )

    return [(row[0], row[1], strength + 5) for row in cursor.fetchall()]


def suggest_org_field(cursor, row, target_field):
    candidates = []

    for source_field, relation_target_field, strength in ORG_RELATION_RULES:
        if relation_target_field != target_field:
            continue

        source_value = clean_org_value(row.get(source_field))

        if not source_value:
            continue

        candidates.extend(query_manager_assignment_relation(
            cursor,
            source_field,
            source_value,
            target_field,
            strength,
        ))
        candidates.extend(query_dim_intern_relation(
            cursor,
            source_field,
            source_value,
            target_field,
            strength,
        ))

    return best_unique_candidate(candidates)


def enrich_org_fields(cursor, row):
    enriched = dict(row)
    ensure_manager_assignments_table(cursor)

    for field_name in ("JefeInmediato", "VP HC", "CC HC", "OI HC", "CIA HC"):
        if clean_org_value(enriched.get(field_name)):
            enriched[field_name] = clean_org_value(enriched.get(field_name))
            continue

        suggestion = suggest_org_field(cursor, enriched, field_name)

        if suggestion:
            enriched[field_name] = suggestion

    return enriched


def upsert_manager_assignment_from_row(cursor, row):
    manager = clean_org_value(row.get("JefeInmediato"))
    key = manager_key(manager)

    if not manager or not key:
        return

    ensure_manager_assignments_table(cursor)

    cursor.execute(
        """
        MERGE dbo.dim_manager_assignments AS target
        USING (
            SELECT
                ? AS jefe_key,
                ? AS jefe_directo,
                ? AS vp,
                ? AS asesor_rh,
                ? AS ubicacion_udn,
                ? AS estado,
                ? AS compania,
                ? AS oi,
                ? AS cc
        ) AS source
        ON target.jefe_key = source.jefe_key
        WHEN MATCHED THEN
            UPDATE SET
                jefe_directo = COALESCE(source.jefe_directo, target.jefe_directo),
                vp = COALESCE(source.vp, target.vp),
                asesor_rh = COALESCE(source.asesor_rh, target.asesor_rh),
                ubicacion_udn = COALESCE(source.ubicacion_udn, target.ubicacion_udn),
                estado = COALESCE(source.estado, target.estado),
                compania = COALESCE(source.compania, target.compania),
                oi = COALESCE(source.oi, target.oi),
                cc = COALESCE(source.cc, target.cc),
                updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN
            INSERT (jefe_key, jefe_directo, vp, asesor_rh, ubicacion_udn, estado, compania, oi, cc)
            VALUES (source.jefe_key, source.jefe_directo, source.vp, source.asesor_rh,
                    source.ubicacion_udn, source.estado, source.compania, source.oi, source.cc);
        """,
        key,
        manager,
        clean_org_value(row.get("VP HC")),
        clean_org_value(row.get("ASESOR RRHH HC")),
        clean_org_value(row.get("UBICACIÓN HC")),
        clean_org_value(row.get("ESTADO UBICACIÓN HC")),
        clean_org_value(row.get("CIA HC")),
        clean_org_value(row.get("OI HC")),
        clean_org_value(row.get("CC HC")),
    )


# ============================================================
# INTERN INSERT / UPDATE
# ============================================================

def insert_or_update_intern(cursor, row, intern_id_override=None):
    row = enrich_org_fields(cursor, row)
    intern_id = intern_id_override or generate_intern_id(row)

    fecha_de_ingreso = clean_date(row.get("FechadeIngreso"))
    fecha_contrato_vence = clean_date(row.get("FechaContratoVence"))

    cursor.execute(
        """
        MERGE dim_interns AS target
        USING (
            SELECT
                ? AS intern_id,
                ? AS num_empleado,
                ? AS num_empleado_cemex,
                ? AS nss,
                ? AS rfc,
                ? AS curp,
                ? AS nombre,
                ? AS paterno,
                ? AS materno,
                ? AS nombre_completo,
                ? AS sexo,
                ? AS edad,
                ? AS universidad,
                ? AS carrera,
                ? AS semestre,
                ? AS puesto,
                ? AS jefe_inmediato,
                ? AS ubicacion_hc,
                ? AS estado_ubicacion_hc,
                ? AS asesor_rrhh_hc,
                ? AS salario_mensual,
                ? AS cc_hc,
                ? AS vp_hc,
                ? AS region_rh,
                ? AS oi_hc,
                ? AS cia_hc,
                ? AS area,
                ? AS status_id,
                ? AS fecha_de_ingreso,
                ? AS fecha_contrato_vence
        ) AS source
        ON target.intern_id = source.intern_id

        WHEN MATCHED THEN
            UPDATE SET
                num_empleado = source.num_empleado,
                num_empleado_cemex = source.num_empleado_cemex,
                nss = source.nss,
                rfc = source.rfc,
                curp = source.curp,
                nombre = source.nombre,
                paterno = source.paterno,
                materno = source.materno,
                nombre_completo = source.nombre_completo,
                sexo = source.sexo,
                edad = source.edad,
                universidad = source.universidad,
                carrera = source.carrera,
                semestre = source.semestre,
                puesto = source.puesto,
                jefe_inmediato = source.jefe_inmediato,
                ubicacion_hc = source.ubicacion_hc,
                estado_ubicacion_hc = source.estado_ubicacion_hc,
                asesor_rrhh_hc = source.asesor_rrhh_hc,
                salario_mensual = source.salario_mensual,
                cc_hc = source.cc_hc,
                vp_hc = source.vp_hc,
                region_rh = source.region_rh,
                oi_hc = source.oi_hc,
                cia_hc = source.cia_hc,
                area = source.area,
                status_id = source.status_id,
                fecha_de_ingreso = source.fecha_de_ingreso,
                fecha_contrato_vence = source.fecha_contrato_vence,
                updated_at = SYSUTCDATETIME()

        WHEN NOT MATCHED THEN
            INSERT (
                intern_id,
                num_empleado,
                num_empleado_cemex,
                nss,
                rfc,
                curp,
                nombre,
                paterno,
                materno,
                nombre_completo,
                sexo,
                edad,
                universidad,
                carrera,
                semestre,
                puesto,
                jefe_inmediato,
                ubicacion_hc,
                estado_ubicacion_hc,
                asesor_rrhh_hc,
                salario_mensual,
                cc_hc,
                vp_hc,
                region_rh,
                oi_hc,
                cia_hc,
                area,
                status_id,
                fecha_de_ingreso,
                fecha_contrato_vence
            )
            VALUES (
                source.intern_id,
                source.num_empleado,
                source.num_empleado_cemex,
                source.nss,
                source.rfc,
                source.curp,
                source.nombre,
                source.paterno,
                source.materno,
                source.nombre_completo,
                source.sexo,
                source.edad,
                source.universidad,
                source.carrera,
                source.semestre,
                source.puesto,
                source.jefe_inmediato,
                source.ubicacion_hc,
                source.estado_ubicacion_hc,
                source.asesor_rrhh_hc,
                source.salario_mensual,
                source.cc_hc,
                source.vp_hc,
                source.region_rh,
                source.oi_hc,
                source.cia_hc,
                source.area,
                source.status_id,
                source.fecha_de_ingreso,
                source.fecha_contrato_vence
            );
        """,
        intern_id,
        clean_value(row.get("NumEmpleado")),
        clean_value(row.get("NumEmpleadoCemex")),
        clean_value(row.get("NSS")),
        clean_value(row.get("RFC")),
        clean_value(row.get("CURP")),
        clean_value(row.get("Nombre")),
        clean_value(row.get("Paterno")),
        clean_value(row.get("Materno")),
        clean_value(row.get("NombreCompleto")),
        clean_value(row.get("Sexo")),
        clean_value(row.get("Edad")),
        clean_value(row.get("Universidad")),
        clean_value(row.get("Carrera")),
        clean_value(row.get("Semestre")),
        clean_value(row.get("Puesto")),
        clean_org_value(row.get("JefeInmediato")),
        clean_value(row.get("UBICACIÓN HC")),
        clean_value(row.get("ESTADO UBICACIÓN HC")),
        clean_value(row.get("ASESOR RRHH HC")),
        clean_value(row.get("SalarioMensual")),
        clean_org_value(row.get("CC HC")),
        clean_org_value(row.get("VP HC")),
        clean_value(row.get("RegionRH")),
        clean_org_value(row.get("OI HC")),
        clean_org_value(row.get("CIA HC")),
        clean_value(row.get("Area")),
        "ST002",
        fecha_de_ingreso,
        fecha_contrato_vence,
    )

    upsert_manager_assignment_from_row(cursor, row)

    return intern_id


def table_has_columns(cursor, table_name, column_names):
    placeholders = ", ".join("?" for _ in column_names)

    cursor.execute(
        f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND TABLE_NAME = ?
          AND COLUMN_NAME IN ({placeholders})
        """,
        table_name,
        *column_names,
    )

    existing_columns = {row[0] for row in cursor.fetchall()}
    return set(column_names).issubset(existing_columns)


def insert_fact_hire_if_available(cursor, intern_id, file_id, process_type_id, row_number, row):
    required_columns = [
        "hire_id",
        "intern_id",
        "source_file_id",
        "process_type_id",
        "source_row_number",
        "hire_status",
        "onboarding_status",
        "accepted_at",
        "start_date",
        "created_at",
    ]

    try:
        if not table_has_columns(cursor, "fact_hires", required_columns):
            return None

        hire_id = "HIRE-" + str(uuid.uuid4())[:8]
        start_date = clean_date(row.get("FechadeIngreso"))

        cursor.execute(
            """
            INSERT INTO fact_hires (
                hire_id,
                intern_id,
                source_file_id,
                process_type_id,
                source_row_number,
                hire_status,
                onboarding_status,
                accepted_at,
                start_date,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME(), ?, SYSUTCDATETIME())
            """,
            hire_id,
            intern_id,
            file_id,
            process_type_id,
            row_number,
            "Accepted",
            "Pending Documents",
            start_date,
        )

        return hire_id
    except Exception as hire_error:
        print("Could not insert fact_hires row; continuing pipeline.")
        print(hire_error)
        return None


def is_current_intern_profile(classification):
    return classification.get("file_profile_id") in {
        "current_interns_excel",
        "current_interns_csv",
    }


def find_matching_current_intern(cursor, row):
    match_fields = [
        ("num_empleado", clean_value(row.get("NumEmpleado"))),
        ("num_empleado_cemex", clean_value(row.get("NumEmpleadoCemex"))),
        ("curp", clean_value(row.get("CURP"))),
        ("rfc", clean_value(row.get("RFC"))),
        ("nss", clean_value(row.get("NSS"))),
    ]
    clauses = []
    params = []

    for column_name, value in match_fields:
        if value is None:
            continue

        clauses.append(f"{column_name} = ?")
        params.append(value)

    if not clauses:
        return None, "No stable identifier was provided."

    cursor.execute(
        f"""
        SELECT TOP 2 intern_id
        FROM dim_interns
        WHERE {" OR ".join(clauses)}
        """,
        *params,
    )

    rows = cursor.fetchall()

    if len(rows) == 1:
        return rows[0][0], None

    if len(rows) > 1:
        return None, "Multiple intern matches found; manual review required."

    return None, "No existing intern matched the stable identifiers."


def normalize_status(value):
    raw_status = clean_value(value)

    if raw_status is None:
        return None

    return (
        str(raw_status)
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def validate_current_intern_lifecycle(row):
    errors = []
    alerts = []
    normalized_status = normalize_status(row.get("Estatus"))
    allowed_statuses = {
        "active",
        "activo",
        "inactive",
        "inactivo",
        "baja",
        "pending",
        "pendiente",
        "accepted",
        "aceptado",
        "extension pending",
        "extension pendiente",
    }
    fecha_vence = clean_date(row.get("FechaContratoVence"))
    today = datetime.now(UTC).date()

    if normalized_status and normalized_status not in allowed_statuses:
        errors.append((
            "VR030",
            "Estatus",
            f"Unknown current intern status: {row.get('Estatus')}",
            "Use active/activo, inactive/inactivo, baja, pending/pendiente, or extension pending."
        ))

    if normalized_status in {"active", "activo"} and fecha_vence and fecha_vence < today:
        errors.append((
            "VR031",
            "FechaContratoVence",
            "Active intern has an expired contract/convenio end date",
            "Confirm baja, extension, or corrected end date."
        ))

    if normalized_status in {"active", "activo"} and fecha_vence:
        days_until_end = (fecha_vence - today).days

        if 0 <= days_until_end <= 30:
            alerts.append((
                "upcoming_expiration",
                "Alert",
                f"Contract/convenio expires in {days_until_end} days."
            ))

    if normalized_status in {"baja", "inactive", "inactivo"}:
        alerts.append((
            "inactive_or_baja",
            "Observed",
            f"Current intern status is {row.get('Estatus')}."
        ))

    return errors, alerts


LEGACY_TO_CANONICAL_FIELDS = {
    "NumEmpleado": "employee_number",
    "NumEmpleadoCemex": "cemex_employee_number",
    "NSS": "nss",
    "RFC": "rfc",
    "CURP": "curp",
    "Nombre": "first_name",
    "Paterno": "paternal_last_name",
    "Materno": "maternal_last_name",
    "NombreCompleto": "full_name",
    "Puesto": "position",
    "JefeInmediato": "manager",
    "SalarioMensual": "salary",
    "CC HC": "cc_hc",
    "VP HC": "vp_hc",
    "RegionRH": "region_rh",
    "OI HC": "oi_hc",
    "CIA HC": "company",
    "RazonSocial": "company",
    "Area": "area",
    "Universidad": "university",
    "Carrera": "career",
    "Semestre": "semester",
    "FechadeIngreso": "start_date",
    "FechaContratoVence": "end_date",
    "Estatus": "status",
    "Sexo": "gender",
    "Edad": "age",
}


def build_canonical_row(row, detected_columns):
    canonical_row = {}

    for source_column, canonical_field in LEGACY_TO_CANONICAL_FIELDS.items():
        value = clean_value(row.get(source_column))

        if value is not None:
            canonical_row[canonical_field] = value

    for column_info in detected_columns:
        canonical_field = column_info.get("canonical_field_name")
        source_column = column_info.get("source_column_name")

        if not canonical_field or not source_column:
            continue

        value = clean_value(row.get(source_column))

        if value is not None:
            canonical_row[canonical_field] = value

    return canonical_row


def append_missing_item_error(error_rows, file_id, file_name, row_number, intern_id, missing_item):
    error_rows.append({
        "source_file_id": file_id,
        "source_file_name": file_name,
        "row_number": row_number,
        "intern_id": intern_id,
        "field_name": missing_item["missing_code"],
        "validation_rule_id": missing_item["missing_type"],
        "error_message": missing_item["missing_description"],
        "suggested_fix": "Provide the missing item or mark it reviewed in the lifecycle workflow.",
        "severity": missing_item["severity"],
        "created_at_utc": utc_now_iso()
    })


def validation_rule_id_for_missing_item(missing_item):
    missing_type = (missing_item or {}).get("missing_type")
    missing_code = (missing_item or {}).get("missing_code")

    if missing_code == "DATE_ORDER":
        return "VR005"
    if missing_type == "BusinessRule":
        return "VR009"
    if missing_type == "Validation":
        return "VR031"
    if missing_type == "Document":
        return "VR022"
    return "VR001"


def process_lifecycle_row(cursor, row, classification, run_id, file_id, row_number, process_type_id=None):
    process_type_id = process_type_id or classification["process_type_id"]
    row_errors = validate_flexible_intern_row(row, process_type_id)
    lifecycle_errors, lifecycle_alerts = validate_current_intern_lifecycle(row)

    if is_current_intern_profile(classification):
        matched_intern_id, match_message = find_matching_current_intern(cursor, row)
        intern_id = matched_intern_id or generate_intern_id(row)

        if not matched_intern_id and match_message != "No existing intern matched the stable identifiers.":
            row_errors.append((
                "VR032",
                "intern_match",
                match_message or "Could not safely match current intern row",
                "Review stable identifiers before updating current intern records."
            ))

            insert_lifecycle_event(
                cursor=cursor,
                run_id=run_id,
                file_id=file_id,
                intern_id=None,
                process_type_id=process_type_id,
                event_type="current_intern_match",
                event_status="Needs Review",
                source_row_number=row_number,
                new_status=clean_value(row.get("Estatus")),
                message=match_message,
                needs_review=1
            )

            return intern_id, row_errors, False

        if row_errors:
            insert_lifecycle_event(
                cursor=cursor,
                run_id=run_id,
                file_id=file_id,
                intern_id=matched_intern_id,
                process_type_id=process_type_id,
                event_type="current_intern_validation",
                event_status="Needs Review",
                source_row_number=row_number,
                new_status=clean_value(row.get("Estatus")),
                message="Current intern row failed validation.",
                needs_review=1
            )

            return matched_intern_id, row_errors, False

        target_intern_id = matched_intern_id or intern_id
        insert_or_update_intern(cursor, row, intern_id_override=target_intern_id)

        insert_lifecycle_event(
            cursor=cursor,
            run_id=run_id,
            file_id=file_id,
            intern_id=target_intern_id,
            process_type_id=process_type_id,
            event_type="current_intern_sync",
            event_status="Updated" if matched_intern_id else "Created",
            source_row_number=row_number,
            new_status=clean_value(row.get("Estatus")),
            message="Current intern record updated from sync file." if matched_intern_id else "Current intern record created from sync file.",
            needs_review=0
        )

        for rule_id, field_name, message, suggested_fix in lifecycle_errors:
            insert_lifecycle_event(
                cursor=cursor,
                run_id=run_id,
                file_id=file_id,
                intern_id=target_intern_id,
                process_type_id=process_type_id,
                event_type="current_intern_review",
                event_status="Needs Review",
                source_row_number=row_number,
                new_status=clean_value(row.get("Estatus")),
                message=message,
                needs_review=1
            )

        for event_type, event_status, message in lifecycle_alerts:
            insert_lifecycle_event(
                cursor=cursor,
                run_id=run_id,
                file_id=file_id,
                intern_id=target_intern_id,
                process_type_id=process_type_id,
                event_type=event_type,
                event_status=event_status,
                source_row_number=row_number,
                new_status=clean_value(row.get("Estatus")),
                message=message,
                needs_review=0
            )

        return target_intern_id, [], True

    intern_id = generate_intern_id(row)

    if row_errors:
        return intern_id, row_errors, False

    insert_or_update_intern(cursor, row)

    if process_type_id in {"PROC_NEW_HIRE", "PROC_ALTA", "new_hire"}:
        hire_id = insert_fact_hire_if_available(
            cursor=cursor,
            intern_id=intern_id,
            file_id=file_id,
            process_type_id=process_type_id,
            row_number=row_number,
            row=row,
        )

        insert_lifecycle_event(
            cursor=cursor,
            run_id=run_id,
            file_id=file_id,
            intern_id=intern_id,
            process_type_id=process_type_id,
            event_type="new_hire_accepted",
            event_status="Accepted",
            source_row_number=row_number,
            old_status=None,
            new_status=clean_value(row.get("Estatus")) or "Accepted",
            message=(
                "Accepted hire row inserted/updated in dim_interns."
                + (f" fact_hires={hire_id}." if hire_id else "")
            ),
            needs_review=0
        )

    return intern_id, [], True


# ============================================================
# MAIN PIPELINE
# ============================================================

def _process_blob(source_container_name=None, source_blob_name=None, run_type="manual"):
    source_container_name = source_container_name or RAW_UPLOADS_CONTAINER

    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING is missing from .env")

    # A full AZURE_SQL_CONNECTION_STRING (used by GitHub Actions) is self-sufficient
    # and does not require the discrete server/database vars. Only require those when
    # no connection string is provided (e.g. local Entra-token auth).
    if not os.getenv("AZURE_SQL_CONNECTION_STRING"):
        if not SQL_SERVER:
            raise ValueError("AZURE_SQL_SERVER is missing from .env")

        if not SQL_DATABASE:
            raise ValueError("AZURE_SQL_DATABASE is missing from .env")

    run_id = generate_run_id()
    log_conn = get_sql_connection()
    log_cursor = log_conn.cursor()
    conn = None
    cursor = None
    file_name = None
    file_id = None
    report_file_id = None
    communication_id = None
    good_rows = 0
    bad_rows = 0
    total_rows = None
    archived_blob_name = None

    insert_pipeline_run(
        cursor=log_cursor,
        run_id=run_id,
        run_type=run_type,
        source_script="pipeline_service.py",
        status="Started",
        source_container=source_container_name,
        source_blob_name=source_blob_name,
    )
    log_conn.commit()

    print(f"Pipeline run started: {run_id}")
    print(f"Pipeline run type: {run_type}")

    blob_service_client = get_blob_service_client()

    container_client = blob_service_client.get_container_client(
        source_container_name
    )

    try:
        if source_blob_name:
            if processed_blob_exists(log_cursor, source_container_name, source_blob_name):
                finish_pipeline_run(
                    cursor=log_cursor,
                    run_id=run_id,
                    status="Skipped",
                    error_message="Blob was already processed."
                )
                log_conn.commit()
                print(f"Already processed: {source_container_name}/{source_blob_name}")
                return {
                    "run_id": run_id,
                    "status": "Skipped",
                    "source_container": source_container_name,
                    "source_blob_name": source_blob_name,
                }

            blob_client = container_client.get_blob_client(source_blob_name)
            blob = SelectedBlob(source_blob_name, blob_client.get_blob_properties())
        else:
            blobs = list(container_client.list_blobs())

            if not blobs:
                finish_pipeline_run(
                    cursor=log_cursor,
                    run_id=run_id,
                    status="Skipped",
                    error_message=f"No files found in {source_container_name}."
                )
                log_conn.commit()
                print(f"No files found in {source_container_name}.")
                return {
                    "run_id": run_id,
                    "status": "Skipped",
                    "source_container": source_container_name,
                    "source_blob_name": None,
                }

            # Process the newest unprocessed uploaded blob first.
            sorted_blobs = sorted(
                blobs,
                key=lambda b: b.last_modified,
                reverse=True
            )

            blob = None
            skipped_processed_blobs = []

            for candidate_blob in sorted_blobs:
                if processed_blob_exists(log_cursor, source_container_name, candidate_blob.name):
                    skipped_processed_blobs.append(candidate_blob.name)
                    continue

                blob = candidate_blob
                break

            if blob is None:
                finish_pipeline_run(
                    cursor=log_cursor,
                    run_id=run_id,
                    status="Skipped",
                    error_message=f"All files in {source_container_name} were already processed."
                )
                log_conn.commit()
                print(f"No unprocessed files found in {source_container_name}.")
                for skipped_blob_name in skipped_processed_blobs[:5]:
                    print(f"Already processed: {source_container_name}/{skipped_blob_name}")
                return {
                    "run_id": run_id,
                    "status": "Skipped",
                    "source_container": source_container_name,
                    "source_blob_name": None,
                }

        file_name = blob.name
        update_pipeline_run_source(
            cursor=log_cursor,
            run_id=run_id,
            source_container=source_container_name,
            source_blob_name=file_name
        )
        log_conn.commit()

        extension = file_name.split(".")[-1].lower()
        mime_type, _ = mimetypes.guess_type(file_name)
        mime_type = mime_type or "unknown"
        size_bytes = blob.size

        file_id = generate_file_id()
        file_type_id = get_file_type_id(extension)
        document_type_id = get_document_type_id(file_name, extension)

        print(f"Processing: {file_name}")
        print(f"Extension: {extension}")
        print(f"MIME: {mime_type}")
        print(f"File Type ID: {file_type_id}")
        print(f"Document Type ID: {document_type_id}")

        os.makedirs(LOCAL_WORK_DIR, exist_ok=True)
        local_path = os.path.join(LOCAL_WORK_DIR, os.path.basename(file_name))

        with open(local_path, "wb") as download_file:
            download_file.write(container_client.download_blob(file_name).readall())

        conn = get_sql_connection()
        cursor = conn.cursor()

        error_rows = []
        missing_items_count = 0
        missing_error_count = 0
        processed_intern_ids = set()
        document_requirement_checks_enabled = False
        document_missing_items_affect_validation = True
        report_file_name = None
        df = None
        sheet_names = []
        metadata_error_message = None

        if extension in {"xlsx", "csv"}:
            try:
                df, sheet_names = flexible_file_classifier.read_tabular_file(
                    local_path,
                    extension
                )
            except Exception as metadata_error:
                metadata_error_message = str(metadata_error)

        classification = flexible_file_classifier.classify_file(
            file_name=file_name,
            extension=extension,
            mime_type=mime_type,
            df=df,
            sheet_names=sheet_names
        )
        inferred_process_type_id = lifecycle_requirements.infer_process_type(
            classification=classification,
            file_name=file_name
        )
        classification.update({
            "run_id": run_id,
            "file_id": file_id,
            "source_container": source_container_name,
            "source_blob_name": file_name,
            "file_name": file_name,
            "file_extension": extension,
            "mime_type": mime_type,
            "classifier_process_type_id": classification.get("process_type_id"),
            "process_type_id": inferred_process_type_id,
        })

        document_type_id = classification["document_type_id"]

        insert_fact_file(
            cursor=cursor,
            file_id=file_id,
            file_name=file_name,
            extension=extension,
            mime_type=mime_type,
            size_bytes=size_bytes,
            file_type_id=file_type_id,
            document_type_id=document_type_id,
            blob_container=source_container_name,
            blob_path=file_name,
            file_status_id="FS004",
            validation_status="Validation In Progress",
            error_message=None,
            send_to_hr=0,
            send_to_coparmex=0
        )

        insert_status_history(
            cursor=cursor,
            entity_type="File",
            entity_id=file_id,
            old_status_id=None,
            new_status_id="ST005",
            changed_by="pipeline",
            change_reason="File validation started"
        )

        insert_file_classification(cursor, classification)

        for column_info in classification.get("detected_columns", []):
            insert_detected_column(
                cursor=cursor,
                run_id=run_id,
                file_id=file_id,
                source_container=source_container_name,
                source_blob_name=file_name,
                column_info=column_info
            )

        print(f"Detected File Profile: {classification['file_profile_id']}")
        print(f"Detected Process Type: {classification['process_type_id']}")
        print(f"Classification Confidence: {classification['classification_confidence']}")
        print(f"Classification Reason: {classification['classification_reason']}")

        if file_type_id is None:
            error_message = "File type is not allowed."
            suggested_fix = "Upload PDF, XLSX, CSV, PNG, JPG, or JPEG."

            insert_validation(
                cursor=cursor,
                file_id=file_id,
                rule_id="VR003",
                field_name="file_extension",
                validation_type="File Validation",
                severity="Error",
                result="Failed",
                error_message=error_message,
                suggested_fix=suggested_fix,
            )

            error_rows.append({
                "source_file_id": file_id,
                "source_file_name": file_name,
                "row_number": None,
                "intern_id": None,
                "field_name": "file_extension",
                "validation_rule_id": "VR003",
                "error_message": error_message,
                "suggested_fix": suggested_fix,
                "created_at_utc": utc_now_iso()
            })

            update_file_status(
                cursor=cursor,
                file_id=file_id,
                file_status_id="FS006",
                validation_status="Validation Failed",
                error_message=error_message,
            )

            insert_status_history(
                cursor=cursor,
                entity_type="File",
                entity_id=file_id,
                old_status_id="ST005",
                new_status_id="ST006",
                changed_by="pipeline",
                change_reason=error_message
            )

        else:
            insert_validation(
                cursor=cursor,
                file_id=file_id,
                rule_id="VR003",
                field_name="file_extension",
                validation_type="File Validation",
                severity="Info",
                result="Passed",
                error_message=None,
                suggested_fix=None,
            )

            if metadata_error_message:
                error_message = f"Could not read tabular file metadata: {metadata_error_message}"
                suggested_fix = "Confirm the file opens correctly and matches an allowed Excel or CSV format."

                insert_validation(
                    cursor=cursor,
                    file_id=file_id,
                    rule_id="VR021",
                    field_name="file_metadata",
                    validation_type="File Classification",
                    severity="Error",
                    result="Failed",
                    error_message=error_message,
                    suggested_fix=suggested_fix,
                )

                error_rows.append({
                    "source_file_id": file_id,
                    "source_file_name": file_name,
                    "row_number": None,
                    "intern_id": None,
                    "field_name": "file_metadata",
                    "validation_rule_id": "VR021",
                    "error_message": error_message,
                    "suggested_fix": suggested_fix,
                    "created_at_utc": utc_now_iso()
                })

                update_file_status(
                    cursor=cursor,
                    file_id=file_id,
                    file_status_id="FS006",
                    validation_status="Validation Failed",
                    error_message=error_message,
                )

                insert_status_history(
                    cursor=cursor,
                    entity_type="File",
                    entity_id=file_id,
                    old_status_id="ST005",
                    new_status_id="ST006",
                    changed_by="pipeline",
                    change_reason=error_message
                )

            elif classification.get("needs_review") and not classification.get("row_processable"):
                error_message = "File was stored but could not be confidently classified."
                suggested_fix = "Review the file manually or rename it with a recognizable document or process type."

                insert_validation(
                    cursor=cursor,
                    file_id=file_id,
                    rule_id="VR022",
                    field_name="file_classification",
                    validation_type="File Classification",
                    severity="Warning",
                    result="Needs Review",
                    error_message=error_message,
                    suggested_fix=suggested_fix,
                )

                insert_intern_document_status(
                    cursor=cursor,
                    intern_id=None,
                    process_type_id=classification["process_type_id"],
                    document_type_id=classification["document_type_id"],
                    file_id=file_id,
                    status="Needs Review",
                    validation_status="Needs Review",
                    notes=classification["classification_reason"]
                )

                error_rows.append({
                    "source_file_id": file_id,
                    "source_file_name": file_name,
                    "row_number": None,
                    "intern_id": None,
                    "field_name": "file_classification",
                    "validation_rule_id": "VR022",
                    "error_message": error_message,
                    "suggested_fix": suggested_fix,
                    "created_at_utc": utc_now_iso()
                })

                update_file_status(
                    cursor=cursor,
                    file_id=file_id,
                    file_status_id="FS006",
                    validation_status="Needs Review",
                    error_message=error_message,
                )

                insert_status_history(
                    cursor=cursor,
                    entity_type="File",
                    entity_id=file_id,
                    old_status_id="ST005",
                    new_status_id="ST006",
                    changed_by="pipeline",
                    change_reason=error_message
                )

                print("File stored and marked as Needs Review.")

            elif extension == "xlsx":
                df, missing_columns = validate_excel_columns(local_path)
                total_rows = len(df)

                if missing_columns and not classification.get("row_processable"):
                    error_message = f"Missing columns: {', '.join(missing_columns)}"
                    suggested_fix = "Update the Excel template with all required columns."

                    insert_validation(
                        cursor=cursor,
                        file_id=file_id,
                        rule_id="VR001",
                        field_name="required_columns",
                        validation_type="Excel Validation",
                        severity="Error",
                        result="Failed",
                        error_message=error_message,
                        suggested_fix=suggested_fix,
                    )

                    for missing_col in missing_columns:
                        error_rows.append({
                            "source_file_id": file_id,
                            "source_file_name": file_name,
                            "row_number": None,
                            "intern_id": None,
                            "field_name": missing_col,
                            "validation_rule_id": "VR001",
                            "error_message": f"Missing required column: {missing_col}",
                            "suggested_fix": "Add this required column to the Excel file.",
                            "created_at_utc": utc_now_iso()
                        })

                    update_file_status(
                        cursor=cursor,
                        file_id=file_id,
                        file_status_id="FS006",
                        validation_status="Validation Failed",
                        error_message="Missing required Excel columns.",
                    )

                    insert_status_history(
                        cursor=cursor,
                        entity_type="File",
                        entity_id=file_id,
                        old_status_id="ST005",
                        new_status_id="ST006",
                        changed_by="pipeline",
                        change_reason="Missing required Excel columns"
                    )

                    print("Excel failed validation because required columns are missing.")
                    print(f"Missing columns: {missing_columns}")

                else:
                    use_flexible_columns = bool(missing_columns)
                    legacy_template_mode = (
                        not use_flexible_columns
                        and classification.get("file_profile_id") == "accepted_hires_excel"
                    )
                    document_requirement_checks_enabled = True
                    document_missing_items_affect_validation = not legacy_template_mode

                    if use_flexible_columns:
                        print("Excel does not match the legacy template exactly.")
                        print("Using flexible canonical column mapping.")
                        print(f"Legacy columns missing: {missing_columns}")

                    insert_validation(
                        cursor=cursor,
                        file_id=file_id,
                        rule_id="VR001",
                        field_name="required_columns",
                        validation_type="Excel Validation",
                        severity="Info",
                        result="Passed",
                        error_message=(
                            "Legacy columns missing, but flexible mapping is being used."
                            if use_flexible_columns else None
                        ),
                        suggested_fix=None,
                    )

                    for index, row in df.iterrows():
                        row_number = index + 2
                        row_to_process = row

                        if use_flexible_columns:
                            row_to_process = flexible_file_classifier.normalize_row_to_legacy(
                                row,
                                classification.get("detected_columns", [])
                            )

                        row_process_type_id = classification["process_type_id"]
                        if is_non_intern_summary_row(row_to_process, row_process_type_id):
                            continue

                        missing_items = []
                        if not legacy_template_mode:
                            canonical_row = build_canonical_row(
                                row_to_process,
                                classification.get("detected_columns", [])
                            )
                            row_process_type_id = lifecycle_requirements.infer_process_type(
                                classification=classification,
                                file_name=file_name,
                                canonical_row=canonical_row
                            )
                            missing_items = lifecycle_requirements.detect_missing_data_for_row(
                                canonical_row,
                                row_process_type_id
                            )

                        blocking_missing_items = [
                            missing_item for missing_item in missing_items
                            if missing_item["severity"] == "Error"
                        ]

                        if blocking_missing_items:
                            intern_id = generate_intern_id(row_to_process)
                            row_errors = [
                                (
                                    validation_rule_id_for_missing_item(missing_item),
                                    missing_item["missing_code"],
                                    missing_item["missing_description"],
                                    "Provide the missing lifecycle requirement."
                                )
                                for missing_item in blocking_missing_items
                            ]
                            row_was_processed = False
                        else:
                            intern_id, row_errors, row_was_processed = process_lifecycle_row(
                                cursor=cursor,
                                row=row_to_process,
                                classification=classification,
                                run_id=run_id,
                                file_id=file_id,
                                row_number=row_number,
                                process_type_id=row_process_type_id
                            )

                        for missing_item in missing_items:
                            missing_items_count += 1
                            if missing_item["severity"] == "Error":
                                missing_error_count += 1

                            lifecycle_requirements.log_missing_item(
                                cursor=cursor,
                                intern_id=intern_id,
                                process_type_id=row_process_type_id,
                                missing_type=missing_item["missing_type"],
                                missing_code=missing_item["missing_code"],
                                missing_description=missing_item["missing_description"],
                                severity=missing_item["severity"],
                                source_file_id=file_id
                            )

                            if missing_item["severity"] != "Error":
                                append_missing_item_error(
                                    error_rows=error_rows,
                                    file_id=file_id,
                                    file_name=file_name,
                                    row_number=row_number,
                                    intern_id=intern_id,
                                    missing_item=missing_item
                                )

                        if row_errors:
                            bad_rows += 1

                            for rule_id, field_name, message, suggested_fix in row_errors:
                                insert_validation(
                                    cursor=cursor,
                                    file_id=file_id,
                                    rule_id=rule_id,
                                    field_name=field_name,
                                    validation_type="Intern Row Validation",
                                    severity="Error",
                                    result="Failed",
                                    error_message=f"Row {row_number}: {message}",
                                    suggested_fix=suggested_fix,
                                    intern_id=None,
                                )

                                error_rows.append({
                                    "source_file_id": file_id,
                                    "source_file_name": file_name,
                                    "row_number": row_number,
                                    "intern_id": intern_id,
                                    "field_name": field_name,
                                    "validation_rule_id": rule_id,
                                    "error_message": message,
                                    "suggested_fix": suggested_fix,
                                    "created_at_utc": utc_now_iso()
                                })

                        elif row_was_processed:
                            processed_intern_ids.add(intern_id)
                            good_rows += 1

                    print(f"Excel rows read: {len(df)}")
                    print(f"Good rows inserted/updated: {good_rows}")
                    print(f"Bad rows logged: {bad_rows}")

                    if bad_rows > 0 or missing_error_count > 0:
                        status_message = f"{bad_rows} rows failed validation."

                        if missing_items_count > 0:
                            status_message = (
                                f"{status_message} {missing_items_count} lifecycle "
                                "missing items detected."
                            )

                        update_file_status(
                            cursor=cursor,
                            file_id=file_id,
                            file_status_id="FS006",
                            validation_status="Validation Failed",
                            error_message=status_message,
                        )

                        insert_status_history(
                            cursor=cursor,
                            entity_type="File",
                            entity_id=file_id,
                            old_status_id="ST005",
                            new_status_id="ST006",
                            changed_by="pipeline",
                            change_reason=status_message
                        )
                    else:
                        update_file_status(
                            cursor=cursor,
                            file_id=file_id,
                            file_status_id="FS005",
                            validation_status="Validation Passed",
                            error_message=None,
                        )

                        insert_status_history(
                            cursor=cursor,
                            entity_type="File",
                            entity_id=file_id,
                            old_status_id="ST005",
                            new_status_id="ST008",
                            changed_by="pipeline",
                            change_reason="File validation passed"
                        )

            elif extension == "csv":
                total_rows = len(df) if df is not None else 0

                insert_validation(
                    cursor=cursor,
                    file_id=file_id,
                    rule_id="VR001",
                    field_name="canonical_columns",
                    validation_type="CSV Validation",
                    severity="Info",
                    result="Passed",
                    error_message="CSV accepted using flexible canonical column mapping.",
                    suggested_fix=None,
                )

                for index, row in df.iterrows():
                    row_number = index + 2
                    row_to_process = flexible_file_classifier.normalize_row_to_legacy(
                        row,
                        classification.get("detected_columns", [])
                    )
                    if is_non_intern_summary_row(row_to_process, classification["process_type_id"]):
                        continue

                    canonical_row = build_canonical_row(
                        row_to_process,
                        classification.get("detected_columns", [])
                    )
                    row_process_type_id = lifecycle_requirements.infer_process_type(
                        classification=classification,
                        file_name=file_name,
                        canonical_row=canonical_row
                    )
                    missing_items = lifecycle_requirements.detect_missing_data_for_row(
                        canonical_row,
                        row_process_type_id
                    )
                    blocking_missing_items = [
                        missing_item for missing_item in missing_items
                        if missing_item["severity"] == "Error"
                    ]

                    if blocking_missing_items:
                        intern_id = generate_intern_id(row_to_process)
                        row_errors = [
                            (
                                validation_rule_id_for_missing_item(missing_item),
                                missing_item["missing_code"],
                                missing_item["missing_description"],
                                "Provide the missing lifecycle requirement."
                            )
                            for missing_item in blocking_missing_items
                        ]
                        row_was_processed = False
                    else:
                        intern_id, row_errors, row_was_processed = process_lifecycle_row(
                            cursor=cursor,
                            row=row_to_process,
                            classification=classification,
                            run_id=run_id,
                            file_id=file_id,
                            row_number=row_number,
                            process_type_id=row_process_type_id
                        )

                    for missing_item in missing_items:
                        missing_items_count += 1
                        if missing_item["severity"] == "Error":
                            missing_error_count += 1

                        lifecycle_requirements.log_missing_item(
                            cursor=cursor,
                            intern_id=intern_id,
                            process_type_id=row_process_type_id,
                            missing_type=missing_item["missing_type"],
                            missing_code=missing_item["missing_code"],
                            missing_description=missing_item["missing_description"],
                            severity=missing_item["severity"],
                            source_file_id=file_id
                        )

                        if missing_item["severity"] != "Error":
                            append_missing_item_error(
                                error_rows=error_rows,
                                file_id=file_id,
                                file_name=file_name,
                                row_number=row_number,
                                intern_id=intern_id,
                                missing_item=missing_item
                            )

                    if row_errors:
                        bad_rows += 1

                        for rule_id, field_name, message, suggested_fix in row_errors:
                            insert_validation(
                                cursor=cursor,
                                file_id=file_id,
                                rule_id=rule_id,
                                field_name=field_name,
                                validation_type="Intern Row Validation",
                                severity="Error",
                                result="Failed",
                                error_message=f"Row {row_number}: {message}",
                                suggested_fix=suggested_fix,
                                # intern_id omitted: intern was never written to dim_interns
                                # so passing it here would violate FK_fact_validations_intern
                                intern_id=None,
                            )

                            error_rows.append({
                                "source_file_id": file_id,
                                "source_file_name": file_name,
                                "row_number": row_number,
                                "intern_id": intern_id,
                                "field_name": field_name,
                                "validation_rule_id": rule_id,
                                "error_message": message,
                                "suggested_fix": suggested_fix,
                                "created_at_utc": utc_now_iso()
                            })
                    elif row_was_processed:
                        processed_intern_ids.add(intern_id)
                        good_rows += 1

                print(f"CSV rows read: {total_rows}")
                print(f"Good rows inserted/updated: {good_rows}")
                print(f"Bad rows logged: {bad_rows}")

                if bad_rows > 0 or missing_error_count > 0:
                    status_message = f"{bad_rows} rows failed validation."

                    if missing_items_count > 0:
                        status_message = (
                            f"{status_message} {missing_items_count} lifecycle "
                            "missing items detected."
                        )

                    update_file_status(
                        cursor=cursor,
                        file_id=file_id,
                        file_status_id="FS006",
                        validation_status="Validation Failed",
                        error_message=status_message,
                    )

                    insert_status_history(
                        cursor=cursor,
                        entity_type="File",
                        entity_id=file_id,
                        old_status_id="ST005",
                        new_status_id="ST006",
                        changed_by="pipeline",
                        change_reason=status_message
                    )
                else:
                    update_file_status(
                        cursor=cursor,
                        file_id=file_id,
                        file_status_id="FS005",
                        validation_status="Validation Passed",
                        error_message=None,
                    )

                    insert_status_history(
                        cursor=cursor,
                        entity_type="File",
                        entity_id=file_id,
                        old_status_id="ST005",
                        new_status_id="ST008",
                        changed_by="pipeline",
                        change_reason="CSV validation passed with flexible mapping."
                    )

            else:
                insert_intern_document_status(
                    cursor=cursor,
                    intern_id=None,
                    process_type_id=classification["process_type_id"],
                    document_type_id=classification["document_type_id"],
                    file_id=file_id,
                    status="Stored",
                    validation_status="Validation Passed",
                    notes=classification["classification_reason"]
                )

                update_file_status(
                    cursor=cursor,
                    file_id=file_id,
                    file_status_id="FS005",
                    validation_status="Validation Passed",
                    error_message=None,
                )

                insert_status_history(
                    cursor=cursor,
                    entity_type="File",
                    entity_id=file_id,
                    old_status_id="ST005",
                    new_status_id="ST008",
                    changed_by="pipeline",
                    change_reason="Non-spreadsheet file validation passed"
                )

        if document_requirement_checks_enabled and processed_intern_ids:
            document_process_ids = {
                "PROC_NEW_HIRE",
                "PROC_ALTA",
                "PROC_EXTENSION",
                "PROC_DOCUMENT_REFRESH",
            }
            process_type_id = classification["process_type_id"]

            if process_type_id in document_process_ids:
                for processed_intern_id in sorted(processed_intern_ids):
                    missing_documents = lifecycle_requirements.detect_missing_documents_for_intern(
                        cursor,
                        processed_intern_id,
                        process_type_id
                    )

                    for missing_document in missing_documents:
                        lifecycle_requirements.log_missing_item(
                            cursor=cursor,
                            intern_id=processed_intern_id,
                            process_type_id=process_type_id,
                            missing_type=missing_document["missing_type"],
                            missing_code=missing_document["missing_code"],
                            missing_description=missing_document["missing_description"],
                            severity=missing_document["severity"],
                            source_file_id=file_id
                        )

                        if document_missing_items_affect_validation:
                            missing_items_count += 1
                            if missing_document["severity"] == "Error":
                                missing_error_count += 1

                            append_missing_item_error(
                                error_rows=error_rows,
                                file_id=file_id,
                                file_name=file_name,
                                row_number=None,
                                intern_id=processed_intern_id,
                                missing_item=missing_document
                            )

                if missing_error_count > 0:
                    update_file_status(
                        cursor=cursor,
                        file_id=file_id,
                        file_status_id="FS006",
                        validation_status="Validation Failed",
                        error_message=(
                            f"{missing_error_count} blocking lifecycle missing items detected."
                        ),
                    )

                    insert_status_history(
                        cursor=cursor,
                        entity_type="File",
                        entity_id=file_id,
                        old_status_id="ST005",
                        new_status_id="ST006",
                        changed_by="pipeline",
                        change_reason=(
                            f"{missing_error_count} blocking lifecycle missing items detected"
                        )
                    )

        # Generate error report if errors exist
        if error_rows:
            report_local_path, report_file_name, report_row_count = create_error_report(
                error_rows=error_rows,
                source_file_id=file_id
            )

            report_blob_path = upload_file_to_blob(
                container_name=ERROR_REPORTS_CONTAINER,
                local_path=report_local_path,
                blob_name=report_file_name
            )

            report_size_bytes = os.path.getsize(report_local_path)
            report_file_id = generate_file_id()

            log_error_report_file(
                cursor=cursor,
                report_file_id=report_file_id,
                report_file_name=report_file_name,
                report_blob_path=report_blob_path,
                report_size_bytes=report_size_bytes
            )

            insert_status_history(
                cursor=cursor,
                entity_type="File",
                entity_id=report_file_id,
                old_status_id=None,
                new_status_id="ST012",
                changed_by="pipeline",
                change_reason=f"Generated error report with {report_row_count} rows"
            )

            print(f"Error report generated: {report_file_name}")
            print(f"Error report uploaded to container: {ERROR_REPORTS_CONTAINER}")

        # MVP 4: prepare communication records
        if error_rows:
            communication_id = prepare_correction_communication(
                cursor=cursor,
                source_file_id=file_id,
                source_file_name=file_name,
                error_report_file_id=report_file_id,
                error_report_name=report_file_name,
                error_count=len(error_rows)
            )

            print(f"Correction communication prepared: {communication_id}")
            try:
                package_id = communication_packager.prepare_correction_package(
                    cursor=cursor,
                    communication_id=communication_id,
                    intern_id=None,
                    process_type_id=classification["process_type_id"],
                    missing_items=[],
                    validation_errors=error_rows,
                    source_file_name=file_name,
                    error_report_file_id=report_file_id,
                )
                print(f"Correction communication package prepared: {package_id}")
            except Exception as package_error:
                print("Communication package metadata could not be prepared:")
                print(package_error)

        else:
            hr_comm_id = prepare_hr_package_communication(
                cursor=cursor,
                source_file_id=file_id,
                source_file_name=file_name,
                good_rows=good_rows
            )

            coparmex_comm_id = prepare_coparmex_package_communication(
                cursor=cursor,
                source_file_id=file_id,
                source_file_name=file_name
            )

            intern_comm_id = prepare_intern_confirmation_communication(
                cursor=cursor,
                source_file_id=file_id,
                source_file_name=file_name,
                good_rows=good_rows
            )

            communication_id = hr_comm_id

            print(f"HR communication prepared: {hr_comm_id}")
            print(f"Coparmex communication prepared: {coparmex_comm_id}")
            print(f"Intern confirmation communication prepared: {intern_comm_id}")
            try:
                package_ids = communication_packager.prepare_success_packages(
                    cursor=cursor,
                    communication_ids={
                        "hr": hr_comm_id,
                        "coparmex": coparmex_comm_id,
                        "applicant": intern_comm_id,
                    },
                    intern_id=None,
                    process_type_id=classification["process_type_id"],
                    intern_context={},
                    validation_summary={
                        "good_rows": good_rows,
                        "bad_rows": bad_rows,
                        "total_rows": total_rows,
                    },
                    files_summary=[],
                )
                print(f"Communication packages prepared: {package_ids}")
            except Exception as package_error:
                print("Communication package metadata could not be prepared:")
                print(package_error)

        blocking_error_rows = [
            error_row for error_row in error_rows
            if error_row.get("severity", "Error") == "Error"
        ]
        validation_passed = bad_rows == 0 and missing_error_count == 0 and len(blocking_error_rows) == 0
        validation_result = "Validation Passed" if validation_passed else "Validation Failed"
        processed_blob_status = "Processed" if validation_passed else "Validation Failed"

        conn.commit()

        try:
            archived_blob_name = archive_processed_blob(
                source_container_name=source_container_name,
                source_blob_name=file_name,
                success=validation_passed
            )
            print(f"Source file archived to: {ARCHIVE_CONTAINER}/{archived_blob_name}")
        except Exception as archive_error:
            print("File processing was committed, but the source file could not be archived:")
            print(archive_error)

            failure_message = str(archive_error)

            finish_pipeline_run(
                cursor=log_cursor,
                run_id=run_id,
                status="Failed",
                archived_blob_name=archived_blob_name,
                source_file_id=file_id,
                error_report_file_id=report_file_id,
                communication_id=communication_id,
                good_rows=good_rows,
                bad_rows=bad_rows,
                total_rows=total_rows,
                error_message=failure_message
            )
            log_conn.commit()
            print("Done. MVP 8A completed: file processed and archive step attempted.")
            return {
                "run_id": run_id,
                "status": "Failed",
                "source_container": source_container_name,
                "source_blob_name": file_name,
                "source_file_id": file_id,
                "error_report_file_id": report_file_id,
                "communication_id": communication_id,
                "good_rows": good_rows,
                "bad_rows": bad_rows,
                "total_rows": total_rows,
                "archived_blob_name": archived_blob_name,
                "error_message": failure_message,
            }

        try:
            update_file_archive_location(
                cursor=cursor,
                file_id=file_id,
                archived_blob_name=archived_blob_name
            )

            insert_status_history(
                cursor=cursor,
                entity_type="File",
                entity_id=file_id,
                old_status_id=None,
                new_status_id="ST012",
                changed_by="pipeline",
                change_reason=(
                    f"Original source blob archived after {validation_result}: "
                    f"{ARCHIVE_CONTAINER}/{archived_blob_name}"
                )
            )

            conn.commit()

            print("SQL original file archive location updated:")
            print(f"- file_id: {file_id}")
            print(f"- blob_container: {ARCHIVE_CONTAINER}")
            print(f"- blob_path: {archived_blob_name}")

        except Exception as archive_sql_error:
            conn.rollback()
            failure_message = (
                "Source blob was archived, but SQL archive location update failed: "
                f"{archive_sql_error}"
            )
            print(failure_message)

            finish_pipeline_run(
                cursor=log_cursor,
                run_id=run_id,
                status="Failed",
                archived_blob_name=archived_blob_name,
                source_file_id=file_id,
                error_report_file_id=report_file_id,
                communication_id=communication_id,
                good_rows=good_rows,
                bad_rows=bad_rows,
                total_rows=total_rows,
                error_message=failure_message
            )
            log_conn.commit()

            return {
                "run_id": run_id,
                "status": "Failed",
                "source_container": source_container_name,
                "source_blob_name": file_name,
                "source_file_id": file_id,
                "error_report_file_id": report_file_id,
                "communication_id": communication_id,
                "good_rows": good_rows,
                "bad_rows": bad_rows,
                "total_rows": total_rows,
                "archived_blob_name": archived_blob_name,
                "error_message": failure_message,
            }

        insert_processed_blob(
            cursor=log_cursor,
            source_container=source_container_name,
            source_blob_name=file_name,
            source_blob_size_bytes=size_bytes,
            source_blob_last_modified=blob.last_modified,
            source_blob_etag=getattr(blob, "etag", None),
            source_file_id=file_id,
            run_id=run_id,
            archived_blob_name=archived_blob_name,
            status=processed_blob_status
        )

        finish_pipeline_run(
            cursor=log_cursor,
            run_id=run_id,
            status="Succeeded",
            archived_blob_name=archived_blob_name,
            source_file_id=file_id,
            error_report_file_id=report_file_id,
            communication_id=communication_id,
            good_rows=good_rows,
            bad_rows=bad_rows,
            total_rows=total_rows,
            error_message=None
        )
        log_conn.commit()
        print("Done. MVP 8A completed: file processed and archive step attempted.")
        return {
            "run_id": run_id,
            "status": "Succeeded",
            "source_container": source_container_name,
            "source_blob_name": file_name,
            "source_file_id": file_id,
            "error_report_file_id": report_file_id,
            "communication_id": communication_id,
            "good_rows": good_rows,
            "bad_rows": bad_rows,
            "total_rows": total_rows,
            "archived_blob_name": archived_blob_name,
            "validation_result": validation_result,
        }
    except Exception as e:
        if conn:
            conn.rollback()

        try:
            if file_name:
                archived_blob_name = archive_processed_blob(
                    source_container_name=source_container_name,
                    source_blob_name=file_name,
                    success=False
                )
                print(f"Failed source file archived to: {ARCHIVE_CONTAINER}/{archived_blob_name}")
        except Exception as archive_error:
            print("Could not archive failed source file:")
            print(archive_error)

        try:
            finish_pipeline_run(
                cursor=log_cursor,
                run_id=run_id,
                status="Failed",
                archived_blob_name=archived_blob_name,
                source_file_id=file_id,
                error_report_file_id=report_file_id,
                communication_id=communication_id,
                good_rows=good_rows,
                bad_rows=bad_rows,
                total_rows=total_rows,
                error_message=str(e)
            )
            log_conn.commit()
        except Exception as log_error:
            log_conn.rollback()
            print("Could not update pipeline run failure log:")
            print(log_error)

        print("Error while processing file:")
        print(e)
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        log_cursor.close()
        log_conn.close()


def _try_onboarding_route(source_container, source_blob_name, run_type):
    """If the blob is a requisición (.docx) or a candidate alta (.xlsx), process it
    through the onboarding pipeline and archive it. Returns a result dict when it
    handled the file, or None so the caller falls back to the intern-data pipeline.
    Centralized here so BOTH the Function App (Event Grid) and the cron route the
    same way."""
    import os as _os
    import tempfile as _tempfile

    ext = _os.path.splitext(source_blob_name or "")[1].lower()
    if ext not in (".docx", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg"):
        return None

    try:
        import onboarding_pipeline
        import document_pipeline

        blob_client = get_blob_service_client().get_blob_client(
            container=source_container, blob=source_blob_name
        )
        metadata = (blob_client.get_blob_properties().metadata) or {}

        with _tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(blob_client.download_blob().readall())
            local_path = tmp.name
    except Exception as setup_error:
        print(f"Onboarding pre-check skipped ({source_blob_name}): {setup_error}")
        return None

    meta = {
        "sender_email": metadata.get("sender_email"),
        "requisition_id": metadata.get("requisition_id") or None,
        "email_subject": metadata.get("email_subject"),
        "body_fields": metadata.get("body_fields"),
        "source_container": source_container,
        "source_blob": source_blob_name,
    }

    try:
        kind = onboarding_pipeline.classify_document(local_path, source_blob_name)

        if kind in ("requisicion", "alta_candidate", "hr_new_hires"):
            try:
                result = onboarding_pipeline.process_onboarding_file(local_path, source_blob_name, meta=meta)
            except Exception as processing_error:
                print(f"Onboarding processing failed for {source_blob_name}: {processing_error}")
                return {"type": "onboarding", "status": "error",
                        "source_blob_name": source_blob_name, "error": str(processing_error)}
        else:
            # documents (candidate package, convenio, signed) — stages C–E
            try:
                result = document_pipeline.process_document(local_path, source_blob_name, meta=meta)
            except Exception as doc_error:
                print(f"Document processing failed for {source_blob_name}: {doc_error}")
                return {"type": "document", "status": "error",
                        "source_blob_name": source_blob_name, "error": str(doc_error)}
            if result is None:
                return None  # not an onboarding document — use the normal pipeline

        try:
            archive_processed_blob(source_container, source_blob_name, success=True)
        except Exception as archive_error:
            print(f"Onboarding archive note: {archive_error}")
        return result
    finally:
        try:
            _os.unlink(local_path)
        except OSError:
            pass


def process_blob_by_name(source_container, source_blob_name, run_type="manual"):
    routed = _try_onboarding_route(source_container, source_blob_name, run_type)
    if routed is not None:
        return routed

    return _process_blob(
        source_container_name=source_container,
        source_blob_name=source_blob_name,
        run_type=run_type,
    )


def process_next_blob(run_type="manual"):
    return _process_blob(
        source_container_name=RAW_UPLOADS_CONTAINER,
        source_blob_name=None,
        run_type=run_type,
    )


def process_all_pending_blobs(run_type="manual", max_files=None):
    results = []
    processed_count = 0

    while max_files is None or processed_count < max_files:
        result = process_next_blob(run_type=run_type)
        results.append(result)

        if not result or result.get("status") == "Skipped":
            break

        processed_count += 1

    return results


def run_pipeline_for_uploaded_file(source_container, source_blob_name, run_type="blob_trigger"):
    return process_blob_by_name(
        source_container=source_container,
        source_blob_name=source_blob_name,
        run_type=run_type,
    )


if __name__ == "__main__":
    process_next_blob(run_type=PIPELINE_RUN_TYPE)
