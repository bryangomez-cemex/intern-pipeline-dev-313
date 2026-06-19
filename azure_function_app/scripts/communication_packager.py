import uuid


RECIPIENT_GROUPS = {
    "applicant": "APPLICANT",
    "current_intern": "APPLICANT",
    "hr": "HR",
    "coparmex": "COPARMEX",
}


def generate_package_id():
    return "PKG-" + str(uuid.uuid4())[:8]


def generate_package_file_id():
    return "PKGF-" + str(uuid.uuid4())[:8]


def build_correction_summary(missing_items, validation_errors, source_file_name):
    lines = [
        f"The uploaded file {source_file_name} needs correction.",
        "",
        f"Validation errors: {len(validation_errors or [])}",
        f"Missing items: {len(missing_items or [])}",
        "",
        "Please review the attached/report metadata and upload a corrected fake-data file.",
    ]

    for item in (missing_items or [])[:10]:
        code = item.get("missing_code") or item.get("field_name") or "MISSING_ITEM"
        description = item.get("missing_description") or item.get("error_message")
        lines.append(f"- {code}: {description}")

    for error in (validation_errors or [])[:10]:
        field = error.get("field_name") or "validation"
        message = error.get("error_message") or "Validation failed."
        lines.append(f"- {field}: {message}")

    return "\n".join(lines)


def build_hr_summary(intern_context, process_type_id, validation_summary, files_summary):
    good_rows = (validation_summary or {}).get("good_rows", 0)
    total_rows = (validation_summary or {}).get("total_rows")

    return (
        f"Intern lifecycle package is ready for HR.\n\n"
        f"Process: {process_type_id}\n"
        f"Accepted rows: {good_rows}\n"
        f"Total rows: {total_rows if total_rows is not None else 'n/a'}\n"
        f"Files selected: {len(files_summary or [])}\n\n"
        "Fake-data package metadata only. No real email has been sent."
    )


def build_coparmex_summary(intern_context, process_type_id):
    return (
        "Coparmex package is ready.\n\n"
        f"Process: {process_type_id}\n"
        "Only Coparmex-required file metadata is included. Internal HR notes are excluded."
    )


def _file_row_to_dict(row, columns):
    return dict(zip(columns, row))


def select_files_for_recipient(cursor, intern_id, process_type_id, recipient_group_id, error_report_file_id=None):
    files = []

    if error_report_file_id and recipient_group_id == "APPLICANT":
        cursor.execute(
            """
            SELECT TOP 1 file_id, blob_container, blob_path, original_file_name
            FROM fact_files
            WHERE file_id = ?
            """,
            error_report_file_id,
        )
        row = cursor.fetchone()
        if row:
            files.append({
                "file_id": row[0],
                "blob_container": row[1],
                "blob_path": row[2],
                "document_code": "ERROR_REPORT",
                "include_reason": "Correction report",
            })

    if not intern_id:
        return files

    requirement_flag = {
        "HR": "required_for_hr",
        "COPARMEX": "required_for_coparmex",
        "APPLICANT": "required_for_applicant",
    }.get(recipient_group_id, "required_for_hr")

    cursor.execute(
        f"""
        SELECT
            ids.file_id,
            f.blob_container,
            f.blob_path,
            rdt.document_code
        FROM fact_intern_document_status ids
        INNER JOIN dim_required_document_types rdt
            ON ids.document_type_id = rdt.required_document_type_id
            OR ids.document_type_id = rdt.document_code
        LEFT JOIN fact_files f
            ON ids.file_id = f.file_id
        WHERE ids.intern_id = ?
          AND ids.process_type_id = ?
          AND rdt.{requirement_flag} = 1
          AND ids.status IN ('Stored', 'Validated', 'Received')
        """,
        intern_id,
        process_type_id,
    )

    for row in cursor.fetchall():
        files.append({
            "file_id": row[0],
            "blob_container": row[1],
            "blob_path": row[2],
            "document_code": row[3],
            "include_reason": f"{recipient_group_id} required document",
        })

    return files


def create_communication_package(cursor, communication_id, intern_id, process_type_id, recipient_group_id, summary_text, files):
    package_id = generate_package_id()

    cursor.execute(
        """
        INSERT INTO fact_communication_packages (
            package_id,
            communication_id,
            intern_id,
            process_type_id,
            recipient_group_id,
            package_status,
            summary_text
        )
        VALUES (?, ?, ?, ?, ?, 'Prepared', ?)
        """,
        package_id,
        communication_id,
        intern_id,
        process_type_id,
        recipient_group_id,
        summary_text,
    )

    for file_info in files or []:
        cursor.execute(
            """
            INSERT INTO fact_communication_package_files (
                package_file_id,
                package_id,
                file_id,
                blob_container,
                blob_path,
                document_code,
                recipient_group_id,
                include_reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            generate_package_file_id(),
            package_id,
            file_info.get("file_id"),
            file_info.get("blob_container"),
            file_info.get("blob_path"),
            file_info.get("document_code"),
            recipient_group_id,
            file_info.get("include_reason"),
        )

    return package_id


def prepare_correction_package(
    cursor,
    communication_id,
    intern_id,
    process_type_id,
    missing_items,
    validation_errors,
    source_file_name,
    error_report_file_id=None,
):
    summary = build_correction_summary(missing_items, validation_errors, source_file_name)
    files = select_files_for_recipient(
        cursor,
        intern_id,
        process_type_id,
        "APPLICANT",
        error_report_file_id=error_report_file_id,
    )

    return create_communication_package(
        cursor,
        communication_id,
        intern_id,
        process_type_id,
        "APPLICANT",
        summary,
        files,
    )


def prepare_success_packages(
    cursor,
    communication_ids,
    intern_id,
    process_type_id,
    intern_context=None,
    validation_summary=None,
    files_summary=None,
):
    package_ids = {}

    applicant_summary = (
        "Your fake-data intern lifecycle file was processed successfully.\n\n"
        "No real email has been sent by default."
    )
    package_ids["applicant"] = create_communication_package(
        cursor,
        communication_ids.get("applicant"),
        intern_id,
        process_type_id,
        "APPLICANT",
        applicant_summary,
        [],
    )

    hr_files = select_files_for_recipient(cursor, intern_id, process_type_id, "HR")
    package_ids["hr"] = create_communication_package(
        cursor,
        communication_ids.get("hr"),
        intern_id,
        process_type_id,
        "HR",
        build_hr_summary(intern_context, process_type_id, validation_summary, hr_files),
        hr_files,
    )

    coparmex_files = select_files_for_recipient(cursor, intern_id, process_type_id, "COPARMEX")
    package_ids["coparmex"] = create_communication_package(
        cursor,
        communication_ids.get("coparmex"),
        intern_id,
        process_type_id,
        "COPARMEX",
        build_coparmex_summary(intern_context, process_type_id),
        coparmex_files,
    )

    return package_ids
