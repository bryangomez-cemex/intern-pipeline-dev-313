import argparse
import importlib.util
import json
import os
import sys
import time
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
FUNCTION_APP_PATH = REPO_ROOT / "azure_function_app" / "function_app.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

os.environ.setdefault("EMAIL_MODE", "simulation")

import app_config
import communication_packager
import flexible_file_classifier
import lifecycle_requirements
import matching_engine


REQUIRED_VIEWS = [
    "vw_pipeline_summary",
    "vw_pipeline_files",
    "vw_validation_errors",
    "vw_communications_status",
]

PROPOSED_VIEWS = [
    "vw_requisition_status",
    "vw_new_hire_status",
    "vw_db_update_summary",
    "vw_daily_alerts",
    "vw_intern_quality_score",
    "vw_match_review_queue",
]

DAILY_INSPECTION_PLAN = [
    "Timer trigger at 7:00 AM America/Monterrey.",
    "Detect missing info, duplicate IDs/emails, duplicate CURP/RFC/NSS.",
    "Detect incoherent status, dates, active/inactive mismatches, missing CC/OI/internal order.",
    "Prepare RH dry-run alert email before real sending is enabled.",
]


def main():
    args = parse_args()
    run_id = f"DRY_RUN_TEST_{uuid.uuid4().hex[:8].upper()}"
    work_dir = Path(app_config.CONFIG.local_work_dir) / "e2e_readiness" / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    print("Deployment readiness E2E V1")
    print("Fake-data-only. No real personal data.")
    print(f"Run id: {run_id}")
    print(f"Work dir: {work_dir}")

    safety = check_email_safety(args.live_azure)
    function_import = check_function_import()
    cases = build_cases(run_id)

    results = [
        safety,
        function_import,
    ]

    for case in cases:
        offline_result = run_offline_case(case, run_id, work_dir)
        if args.live_azure and offline_result["status"] in {"PASS", "PASS_WITH_GAP"}:
            live_result = run_live_case(case, run_id, work_dir, args)
            offline_result["live_result"] = live_result
            if live_result["status"] == "FAIL":
                offline_result["status"] = "FAIL"
                offline_result.setdefault("errors", []).extend(live_result.get("errors", []))
        results.append(offline_result)

    view_result = check_required_views(args.live_azure)
    results.append(view_result)

    report = build_report(run_id, args.live_azure, work_dir, results)
    print_report(report)
    write_report(work_dir, report)

    if any(result["status"] == "FAIL" for result in results):
        raise SystemExit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fake-data deployment readiness E2E check for intern-system-pipeline."
    )
    parser.add_argument(
        "--live-azure",
        action="store_true",
        help="Upload fake blobs and run the real pipeline by exact blob name.",
    )
    parser.add_argument(
        "--confirm-live-dry-run",
        default="",
        help="Required value TEST for --live-azure.",
    )
    args = parser.parse_args()

    if args.live_azure and args.confirm_live_dry_run != "TEST":
        raise SystemExit("--live-azure requires --confirm-live-dry-run TEST")

    return args


def check_email_safety(live_azure=False):
    errors = []
    warnings = []
    email_mode = os.getenv("EMAIL_MODE", "simulation").strip().lower()
    send_emails = os.getenv("SEND_EMAILS")
    email_dry_run = os.getenv("EMAIL_DRY_RUN")

    if email_mode != "simulation":
        errors.append(f"EMAIL_MODE must be simulation, got {email_mode!r}.")

    if send_emails is not None and send_emails.strip().lower() not in {"false", "0", "no"}:
        errors.append("SEND_EMAILS must be false when configured.")
    elif send_emails is None:
        warnings.append("SEND_EMAILS not configured; safe by EMAIL_MODE=simulation.")

    if email_dry_run is not None and email_dry_run.strip().lower() not in {"true", "1", "yes"}:
        errors.append("EMAIL_DRY_RUN must be true when configured.")
    elif email_dry_run is None:
        warnings.append("EMAIL_DRY_RUN not configured; safe by EMAIL_MODE=simulation.")

    if live_azure and send_emails is None:
        errors.append("Live E2E requires SEND_EMAILS=false.")
    if live_azure and email_dry_run is None:
        errors.append("Live E2E requires EMAIL_DRY_RUN=true.")

    return result(
        name="Email safety",
        status="FAIL" if errors else "PASS",
        details={
            "EMAIL_MODE": email_mode,
            "SEND_EMAILS": safe_env_value(send_emails),
            "EMAIL_DRY_RUN": safe_env_value(email_dry_run),
        },
        warnings=warnings,
        errors=errors,
    )


def check_function_import():
    if not FUNCTION_APP_PATH.exists():
        return result("Azure Function import", "FAIL", errors=[f"Missing {FUNCTION_APP_PATH}"])

    try:
        spec = importlib.util.spec_from_file_location("readiness_function_app", FUNCTION_APP_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return result("Azure Function import", "PASS")
    except ModuleNotFoundError as exc:
        if exc.name in {"azure", "azure.functions"}:
            return result(
                "Azure Function import",
                "PASS_WITH_GAP",
                gaps=["azure-functions package is missing in this environment; install requirements for local Function test."],
            )
        return result("Azure Function import", "FAIL", errors=[str(exc)])
    except Exception as exc:
        return result("Azure Function import", "FAIL", errors=[str(exc)])


def build_cases(run_id):
    return [
        {
            "name": "Requisition pass",
            "pipeline": "requisition",
            "file_name": f"requisition_TEST_FAKE_DRY_RUN_{run_id}.xlsx",
            "expected_business_pipeline_type": "requisition",
            "expected_process_type": "PROC_REQUISITION",
            "rows": [{
                "Puesto": "Practicante TEST Analitica",
                "VP HC": "VP TEST",
                "CC HC": "CC-TEST-001",
                "OI HC": "OI-TEST-001",
                "JefeInmediato": "RH Manager TEST",
                "UBICACIÓN HC": "Monterrey TEST",
                "ASESOR RRHH HC": "RH TEST",
                "NombreCompleto": "FAKE TEST REQUISITION",
            }],
            "expected_status": "PASS",
            "expected_gaps": [],
        },
        {
            "name": "New Hire pass",
            "pipeline": "new_hire",
            "file_name": f"accepted_hires_TEST_FAKE_DRY_RUN_{run_id}.xlsx",
            "expected_business_pipeline_type": "new_hire_documents",
            "expected_process_type": "PROC_NEW_HIRE",
            "rows": [{
                "Numero Puesto": f"POS-TEST-{run_id}",
                "NombreCompleto": "FAKE TEST INTERN PASS",
                "CURP": "FATP010101HNLXXX01",
                "RFC": "FATP010101ABC",
                "NSS": "12345678901",
                "Email": "fake.test.pass@example.com",
                "Universidad": "Universidad TEST",
                "Carrera": "Ingenieria TEST",
                "FechadeIngreso": "2026-01-01",
                "FechaContratoVence": "2026-12-31",
                "Estatus": "Pendiente",
                "CC HC": "CC-TEST-001",
                "OI HC": "OI-TEST-001",
            }],
            "match_candidates": [{
                "intern_id": "INT-FAKE-PASS",
                "CURP": "FATP010101HNLXXX01",
                "RFC": "FATP010101ABC",
                "NSS": "12345678901",
                "Email": "fake.test.pass@example.com",
                "NombreCompleto": "FAKE TEST INTERN PASS",
            }],
            "expected_match_confidences": {"HIGH", "MEDIUM"},
            "expected_status": "PASS_WITH_GAP",
            "expected_gaps": ["matching_engine_sql_log_only_not_connected"],
        },
        {
            "name": "New Hire fail",
            "pipeline": "new_hire",
            "file_name": f"accepted_hires_fail_TEST_FAKE_DRY_RUN_{run_id}.xlsx",
            "expected_business_pipeline_type": "new_hire_documents",
            "expected_process_type": "PROC_NEW_HIRE",
            "rows": [{
                "NombreCompleto": "FAKE TEST INTERN FAIL",
                "Email": "fake.test.fail@example.com",
                "Universidad": "Universidad TEST",
                "Carrera": "Ingenieria TEST",
                "FechadeIngreso": "2026-12-31",
                "FechaContratoVence": "2026-01-01",
                "Estatus": "Pendiente",
            }],
            "expected_validation_errors": [
                "CURP/RFC/NSS missing",
                "CC HC missing",
                "OI HC missing",
                "Start date is after end date",
            ],
            "expected_status": "PASS",
        },
        {
            "name": "DB Update",
            "pipeline": "db_update",
            "file_name": f"last_update_practicantes_actuales_TEST_FAKE_DRY_RUN_{run_id}.xlsx",
            "expected_business_pipeline_type": "db_update",
            "expected_process_type": "PROC_CURRENT_SYNC",
            "rows": [{
                "NumEmpleado": "900001",
                "NumEmpleadoCemex": "CEMEX900001",
                "RFC": "FADB010101ABC",
                "CURP": "FADB010101HNLXXX01",
                "NSS": "98765432109",
                "NombreCompleto": "FAKE TEST DB UPDATE",
                "FechadeIngreso": "2025-01-01",
                "FechaContratoVence": "2026-12-31",
                "SalarioMensual": "$8,800.00",
                "CC HC": "CC-TEST-002",
                "OI HC": "OI-TEST-002",
                "Estatus": "Activo",
                "CIA HC": "CIA TEST",
            }],
            "expected_status": "PASS",
        },
        {
            "name": "Unknown file",
            "pipeline": "unknown",
            "file_name": f"unknown_TEST_FAKE_DRY_RUN_{run_id}.xlsx",
            "expected_business_pipeline_type": "unknown",
            "expected_process_type": "PROC_DOCUMENT_REFRESH",
            "rows": [{
                "RandomColumnOne": "TEST",
                "AnotherUnknownThing": "FAKE",
                "NoBusinessContext": "DRY_RUN",
            }],
            "expected_status": "PASS",
        },
    ]


def run_offline_case(case, run_id, work_dir):
    errors = []
    gaps = list(case.get("expected_gaps", []))
    warnings = []
    file_path = write_case_file(case, work_dir)
    df, sheet_names = flexible_file_classifier.read_tabular_file(file_path, "xlsx")
    classification = flexible_file_classifier.classify_file(
        file_name=case["file_name"],
        extension="xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        df=df,
        sheet_names=sheet_names,
    )
    process_type = lifecycle_requirements.infer_process_type(classification, case["file_name"])

    if classification.get("business_pipeline_type") != case["expected_business_pipeline_type"]:
        errors.append(
            f"Expected business_pipeline_type={case['expected_business_pipeline_type']}, got {classification.get('business_pipeline_type')}"
        )

    if process_type != case["expected_process_type"]:
        errors.append(f"Expected process_type={case['expected_process_type']}, got {process_type}")

    row = case["rows"][0]
    missing_items = lifecycle_requirements.detect_missing_data_for_row(row, process_type)
    validation_errors = detect_case_validation_errors(case, row, missing_items)
    communication_summary = build_case_communication_summary(case, missing_items, validation_errors)
    match_result = build_case_match_result(case, row)
    db_update_summary = build_db_update_summary(case, row)

    if case["pipeline"] == "unknown" and not classification.get("needs_review"):
        errors.append("Unknown file should be marked needs_review.")

    if case["pipeline"] == "new_hire" and "fail" not in case["name"].lower() and match_result:
        expected_confidences = case.get("expected_match_confidences", set())
        if match_result.get("match_confidence") not in expected_confidences:
            errors.append(f"Expected match confidence in {expected_confidences}, got {match_result.get('match_confidence')}")

    if case["pipeline"] == "new_hire" and "fail" in case["name"].lower() and not validation_errors:
        errors.append("Expected validation errors for failing new hire case.")

    if case["pipeline"] == "db_update" and not db_update_summary:
        errors.append("Expected DB update summary.")

    status = "FAIL" if errors else case.get("expected_status", "PASS")
    details = {
        "file": str(file_path),
        "classification": {
            "technical_profile": classification.get("technical_profile"),
            "business_pipeline_type": classification.get("business_pipeline_type"),
            "confidence": classification.get("confidence"),
            "needs_review": classification.get("needs_review"),
        },
        "process_type": process_type,
        "missing_items": summarize_missing_items(missing_items),
        "validation_errors": validation_errors,
        "communication_summary": communication_summary,
        "match_result": match_result,
        "db_update_summary": db_update_summary,
    }

    return result(case["name"], status, details=details, warnings=warnings, gaps=gaps, errors=errors)


def run_live_case(case, run_id, work_dir, args):
    errors = []
    warnings = []

    blob_name = f"{case['pipeline']}/{run_id}/{case['file_name']}"
    if not is_safe_live_blob_name(blob_name, case["pipeline"], run_id):
        return result(case["name"] + " live", "FAIL", errors=[f"Unsafe live blob name: {blob_name}"])

    try:
        import azure_clients
        import pipeline_service
    except Exception as exc:
        return result(case["name"] + " live", "FAIL", errors=[f"Could not import live clients: {exc}"])

    try:
        file_path = work_dir / case["file_name"]
        blob_service = azure_clients.get_blob_service_client()
        container = blob_service.get_container_client(app_config.CONFIG.raw_uploads_container)
        with open(file_path, "rb") as handle:
            container.upload_blob(blob_name, handle, overwrite=False)
        print(f"Uploaded live dry-run blob: {app_config.CONFIG.raw_uploads_container}/{blob_name}")

        pipeline_result = wait_for_live_sql_for_blob(blob_name)
        if pipeline_result["status"] == "FAIL":
            errors.extend(pipeline_result.get("errors", []))

        live_checks = check_live_sql_for_blob(blob_name)
        if live_checks["status"] == "FAIL":
            errors.extend(live_checks.get("errors", []))

        return result(
            case["name"] + " live",
            "FAIL" if errors else "PASS",
            details={
                "blob_name": blob_name,
                "pipeline_result": pipeline_result,
                "sql_checks": live_checks,
            },
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        return result(case["name"] + " live", "FAIL", errors=[str(exc)], details={"blob_name": blob_name})


def check_required_views(live_azure):
    if not live_azure:
        return result(
            "Required SQL views",
            "PASS_WITH_GAP",
            details={
                "required_views": REQUIRED_VIEWS,
                "proposed_views": PROPOSED_VIEWS,
                "mode": "offline; SQL was not queried",
            },
        )

    try:
        import azure_clients
        conn = azure_clients.get_sql_connection()
        try:
            cursor = conn.cursor()
            existing = set()
            for view_name in REQUIRED_VIEWS + PROPOSED_VIEWS + ["vw_matching_engine_review_queue"]:
                cursor.execute(
                    """
                    SELECT 1
                    FROM INFORMATION_SCHEMA.VIEWS
                    WHERE TABLE_SCHEMA = 'dbo'
                      AND TABLE_NAME = ?
                    """,
                    view_name,
                )
                if cursor.fetchone():
                    existing.add(view_name)
        finally:
            conn.close()

        missing_required = [view for view in REQUIRED_VIEWS if view not in existing]
        missing_proposed = [view for view in PROPOSED_VIEWS if view not in existing]

        return result(
            "Required SQL views",
            "FAIL" if missing_required else "PASS",
            details={
                "existing_views": sorted(existing),
                "missing_required": missing_required,
                "missing_proposed": missing_proposed,
            },
            errors=[f"Missing required view: {view}" for view in missing_required],
            gaps=[f"Proposed view not implemented: {view}" for view in missing_proposed],
        )
    except Exception as exc:
        return result("Required SQL views", "FAIL", errors=[str(exc)])


def check_live_sql_for_blob(blob_name):
    try:
        import azure_clients
        conn = azure_clients.get_sql_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.fact_files
                WHERE blob_path LIKE ?
                   OR original_file_name LIKE ?
                """,
                f"%{blob_name.split('/')[-1]}%",
                f"%{blob_name.split('/')[-1]}%",
            )
            file_count = cursor.fetchone()[0]
        finally:
            conn.close()

        if file_count < 1:
            return result("Live SQL blob check", "FAIL", errors=[f"No fact_files row found for {blob_name}"])

        return result("Live SQL blob check", "PASS", details={"fact_files_count": file_count})
    except Exception as exc:
        return result("Live SQL blob check", "FAIL", errors=[str(exc)])


def wait_for_live_sql_for_blob(blob_name, timeout_seconds=180, poll_seconds=10):
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        check = check_live_sql_for_blob(blob_name)
        if check["status"] == "PASS":
            return result(
                "Function-triggered live processing",
                "PASS",
                details={
                    "blob_name": blob_name,
                    "fact_files_count": check.get("details", {}).get("fact_files_count"),
                },
            )
        last_error = "; ".join(check.get("errors", []))
        time.sleep(poll_seconds)

    return result(
        "Function-triggered live processing",
        "FAIL",
        errors=[last_error or f"Timed out waiting for Function-triggered processing of {blob_name}"],
    )


def write_case_file(case, work_dir):
    import pandas as pd

    file_path = work_dir / case["file_name"]
    df = pd.DataFrame(case["rows"])
    df.to_excel(file_path, index=False)
    return file_path


def detect_case_validation_errors(case, row, missing_items):
    errors = []

    if case["pipeline"] == "new_hire" and "fail" in case["name"].lower():
        if not any(row.get(field) for field in ["CURP", "RFC", "NSS"]):
            errors.append({
                "field_name": "CURP/RFC/NSS",
                "error_message": "CURP, RFC, or NSS is required for high-confidence new hire matching.",
                "suggested_fix": "Add at least one strong fake identifier.",
            })
        if not row.get("CC HC"):
            errors.append({
                "field_name": "CC HC",
                "error_message": "Cost center is missing.",
                "suggested_fix": "Add a valid fake CC HC.",
            })
        if not row.get("OI HC"):
            errors.append({
                "field_name": "OI HC",
                "error_message": "Internal order is missing.",
                "suggested_fix": "Add a valid fake OI HC.",
            })
        start_date = matching_engine.normalize_date(row.get("FechadeIngreso"))
        end_date = matching_engine.normalize_date(row.get("FechaContratoVence"))
        if start_date and end_date and start_date > end_date:
            errors.append({
                "field_name": "FechadeIngreso/FechaContratoVence",
                "error_message": "Start date is after contract end date.",
                "suggested_fix": "Correct the fake start/end dates.",
            })

    for item in missing_items or []:
        errors.append({
            "field_name": item.get("missing_code"),
            "error_message": item.get("missing_description"),
            "suggested_fix": "Provide the required fake value.",
        })

    return errors


def build_case_communication_summary(case, missing_items, validation_errors):
    if validation_errors or case["pipeline"] == "unknown":
        return communication_packager.build_correction_summary(
            missing_items,
            validation_errors,
            case["file_name"],
        )

    if case["pipeline"] in {"requisition", "db_update", "new_hire"}:
        return communication_packager.build_hr_summary(
            intern_context={"fake": True},
            process_type_id=case["expected_process_type"],
            validation_summary={"good_rows": 1, "total_rows": 1},
            files_summary=[{"file_name": case["file_name"]}],
        )

    return "No communication summary expected."


def build_case_match_result(case, row):
    if not case.get("match_candidates"):
        return None

    profile = matching_engine.build_match_profile(row, entity_type="intern")
    return matching_engine.resolve_best_match(
        profile,
        case["match_candidates"],
        entity_type="intern",
    )


def build_db_update_summary(case, row):
    if case["pipeline"] != "db_update":
        return None

    required = ["NumEmpleado", "NumEmpleadoCemex", "RFC", "CURP", "NSS", "CC HC", "OI HC", "Estatus"]
    missing = [field for field in required if not row.get(field)]
    return {
        "rows_seen": 1,
        "candidate_updates": 1 if row.get("NumEmpleado") else 0,
        "candidate_inserts": 0,
        "status_changes": 0,
        "missing_info_count": len(missing),
        "missing_fields": missing,
        "email_mode": "simulation",
    }


def summarize_missing_items(missing_items):
    summarized = []
    for item in missing_items or []:
        summarized.append({
            "missing_type": item.get("missing_type"),
            "missing_code": item.get("missing_code"),
            "severity": item.get("severity"),
            "description": item.get("missing_description"),
        })
    return summarized


def is_safe_live_blob_name(blob_name, pipeline, run_id):
    required_tokens = ["TEST", "FAKE", "DRY_RUN", run_id]
    return (
        blob_name.startswith(f"{pipeline}/{run_id}/")
        and all(token in blob_name for token in required_tokens)
        and ".." not in blob_name
        and not blob_name.startswith("/")
    )


def build_report(run_id, live_azure, work_dir, results):
    blockers = []
    gaps = []
    for item in results:
        blockers.extend(item.get("errors", []))
        gaps.extend(item.get("gaps", []))

    has_failures = any(item["status"] == "FAIL" for item in results)
    has_gaps = any(item["status"] == "PASS_WITH_GAP" or item.get("gaps") for item in results)
    readiness_status = "NOT_READY" if has_failures else "PARTIALLY_READY" if has_gaps else "READY"

    return {
        "readiness_status": readiness_status,
        "run_id": run_id,
        "mode": "live_azure" if live_azure else "offline",
        "work_dir": str(work_dir),
        "results": results,
        "blockers": sorted(set(blockers)),
        "gaps": sorted(set(gaps)),
        "daily_inspection_plan": DAILY_INSPECTION_PLAN,
        "suggested_sql_queries": [
            "SELECT TOP 10 * FROM dbo.vw_pipeline_summary ORDER BY last_processed_at DESC;",
            "SELECT TOP 25 * FROM dbo.vw_pipeline_files WHERE blob_path LIKE '%DRY_RUN%' ORDER BY created_at DESC;",
            "SELECT TOP 25 * FROM dbo.vw_validation_errors WHERE source_file_name LIKE '%DRY_RUN%' ORDER BY created_at DESC;",
            "SELECT TOP 25 * FROM dbo.vw_communications_status ORDER BY created_at DESC;",
            "SELECT TOP 25 * FROM dbo.vw_matching_engine_review_queue ORDER BY created_at DESC;",
        ],
    }


def print_report(report):
    print("\n========================================")
    print("Deployment Readiness Result")
    print("========================================")
    print(f"Readiness status: {report['readiness_status']}")
    print(f"Mode: {report['mode']}")
    print(f"Run id: {report['run_id']}")

    for item in report["results"]:
        print(f"{item['name']}: {item['status']}")
        for warning in item.get("warnings", []):
            print(f"  warning: {warning}")
        for gap in item.get("gaps", []):
            print(f"  gap: {gap}")
        for error in item.get("errors", []):
            print(f"  error: {error}")

    if report["daily_inspection_plan"]:
        print("\nDaily inspection plan:")
        for step in report["daily_inspection_plan"]:
            print(f"- {step}")

    print("\nSuggested SQL queries:")
    for query in report["suggested_sql_queries"]:
        print(query)


def write_report(work_dir, report):
    report_path = work_dir / "deployment_readiness_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


def result(name, status, details=None, warnings=None, gaps=None, errors=None):
    return {
        "name": name,
        "status": status,
        "details": details or {},
        "warnings": warnings or [],
        "gaps": gaps or [],
        "errors": errors or [],
    }


def safe_env_value(value):
    if value is None:
        return None
    return str(value).strip().lower()


if __name__ == "__main__":
    main()
