import importlib
import importlib.util
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
FUNCTION_APP_DIR = REPO_ROOT / "azure_function_app"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def print_section(title):
    print("\n========================================")
    print(title)
    print("========================================")


def require_import(module_name):
    try:
        module = importlib.import_module(module_name)
        print(f"Import {module_name}: OK")
        return module
    except ModuleNotFoundError as exc:
        missing_name = exc.name or module_name
        print(f"Import {module_name}: FAILED")
        print(f"Missing dependency/module: {missing_name}")
        print("Install local dependencies with:")
        print("python3 -m pip install -r requirements.txt")
        raise


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"{label}: OK ({actual})")


def assert_true(value, label):
    if not value:
        raise AssertionError(f"{label}: expected truthy value, got {value!r}")
    print(f"{label}: OK")


def dataframe(pandas_module, columns):
    return pandas_module.DataFrame([{column: "fake" for column in columns}])


def check_imports():
    print_section("Imports")
    modules = {
        "pipeline_service": require_import("pipeline_service"),
        "onboarding_pipeline": require_import("onboarding_pipeline"),
        "document_pipeline": require_import("document_pipeline"),
        "requisition_parser": require_import("requisition_parser"),
        "flexible_file_classifier": require_import("flexible_file_classifier"),
        "lifecycle_requirements": require_import("lifecycle_requirements"),
        "matching_engine": require_import("matching_engine"),
        "communication_packager": require_import("communication_packager"),
        "app_config": require_import("app_config"),
        "pandas": require_import("pandas"),
    }

    for function_name in [
        "process_blob_by_name",
        "process_next_blob",
        "process_all_pending_blobs",
        "run_pipeline_for_uploaded_file",
    ]:
        assert_true(
            hasattr(modules["pipeline_service"], function_name),
            f"pipeline_service.{function_name} exists",
        )

    return modules


def check_entrypoint_imports():
    print_section("Entrypoints")
    process_blob_file = REPO_ROOT / "scripts" / "process_blob_file.py"
    function_app = FUNCTION_APP_DIR / "function_app.py"

    assert_true(process_blob_file.exists(), "scripts/process_blob_file.py exists")
    assert_true(function_app.exists(), "azure_function_app/function_app.py exists")

    require_import("process_blob_file")

    try:
        function_app_spec = importlib.util.spec_from_file_location(
            "smoke_function_app",
            function_app,
        )
        function_app_module = importlib.util.module_from_spec(function_app_spec)
        function_app_spec.loader.exec_module(function_app_module)
        print("Azure Function app import: OK")
    except ModuleNotFoundError as exc:
        if exc.name in {"azure", "azure.functions"}:
            print("Azure Function app import: WARNING")
            print("azure-functions is not installed in this Python environment.")
            print("Install local dependencies with:")
            print("python3 -m pip install -r azure_function_app/requirements.txt")
            return
        raise


def check_email_mode_default(app_config_module):
    print_section("Email Safety")
    configured_email_mode = app_config_module.CONFIG.email_mode
    default_email_mode = os.getenv("EMAIL_MODE", "simulation").strip().lower()

    assert_equal(default_email_mode, configured_email_mode, "App config EMAIL_MODE matches environment/default")

    if "EMAIL_MODE" not in os.environ:
        assert_equal(configured_email_mode, "simulation", "EMAIL_MODE default")
    elif configured_email_mode == "simulation":
        print("EMAIL_MODE configured safely: simulation")
    else:
        print(f"EMAIL_MODE configured as {configured_email_mode!r}; smoke test did not send email.")


def classify_case(classifier, lifecycle, pandas_module, case):
    df = dataframe(pandas_module, case["columns"]) if case["columns"] is not None else None
    classification = classifier.classify_file(
        file_name=case["file_name"],
        extension=case["extension"],
        mime_type=case["mime_type"],
        df=df,
        sheet_names=case.get("sheet_names", []),
    )
    process_type = lifecycle.infer_process_type(
        classification=classification,
        file_name=case["file_name"],
    )

    print(f"\nCase: {case['name']}")
    assert_equal(
        classification["file_profile_id"],
        case["expected_profile"],
        "file_profile_id",
    )
    assert_equal(
        classification["technical_profile"],
        case["expected_profile"],
        "technical_profile",
    )
    assert_equal(
        classification["business_pipeline_type"],
        case["expected_business_pipeline_type"],
        "business_pipeline_type",
    )
    assert_equal(process_type, case["expected_process_type"], "process_type")

    if "expected_needs_review" in case:
        assert_equal(
            classification["needs_review"],
            case["expected_needs_review"],
            "needs_review",
        )


def check_classifier_routes(classifier, lifecycle, pandas_module):
    print_section("Classifier Routes")
    cases = [
        {
            "name": "accepted hires Excel",
            "file_name": "accepted_hires_fake.xlsx",
            "extension": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "columns": [
                "NombreCompleto",
                "Universidad",
                "Carrera",
                "FechadeIngreso",
                "FechaContratoVence",
                "Estatus",
            ],
            "expected_profile": "accepted_hires_excel",
            "expected_business_pipeline_type": "new_hire_documents",
            "expected_process_type": "PROC_NEW_HIRE",
            "expected_needs_review": False,
        },
        {
            "name": "requisition Excel",
            "file_name": "requisition_puesto_fake.xlsx",
            "extension": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "columns": ["Puesto", "Manager", "OI HC", "CC HC", "VP HC"],
            "expected_profile": "requisition_excel",
            "expected_business_pipeline_type": "requisition",
            "expected_process_type": "PROC_REQUISITION",
            "expected_needs_review": False,
        },
        {
            "name": "current interns DB update Excel",
            "file_name": "last_update_practicantes_actuales.xlsx",
            "extension": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "columns": ["NumEmpleado", "Estatus", "FechaContratoVence", "OI HC", "CC HC"],
            "expected_profile": "current_interns_excel",
            "expected_business_pipeline_type": "db_update",
            "expected_process_type": "PROC_CURRENT_SYNC",
            "expected_needs_review": False,
        },
        {
            "name": "current interns roster Excel",
            "file_name": "practicantes_actuales.xlsx",
            "extension": "xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "columns": ["NumEmpleado", "Estatus", "FechaContratoVence", "OI HC", "CC HC"],
            "expected_profile": "current_interns_excel",
            "expected_business_pipeline_type": "current_interns",
            "expected_process_type": "PROC_CURRENT_SYNC",
            "expected_needs_review": False,
        },
        {
            "name": "unknown allowed PDF",
            "file_name": "mystery_upload.pdf",
            "extension": "pdf",
            "mime_type": "application/pdf",
            "columns": None,
            "expected_profile": "generic_pdf",
            "expected_business_pipeline_type": "unknown",
            "expected_process_type": "PROC_DOCUMENT_REFRESH",
            "expected_needs_review": True,
        },
        {
            "name": "invalid executable extension",
            "file_name": "not_allowed.exe",
            "extension": "exe",
            "mime_type": "application/x-msdownload",
            "columns": None,
            "expected_profile": "unknown_file",
            "expected_business_pipeline_type": "invalid_file",
            "expected_process_type": "PROC_DOCUMENT_REFRESH",
            "expected_needs_review": True,
        },
    ]

    for case in cases:
        classify_case(classifier, lifecycle, pandas_module, case)


def check_corporate_column_aliases(classifier, pandas_module):
    print_section("Corporate Column Aliases")
    df = dataframe(pandas_module, [
        "NUMERO",
        "NOMBRE",
        "CODPOS",
        "CVEPTO",
        "DESCRIPCIONPUESTO",
        "VICEPRESIDENCIA",
        "REGIONAREA",
        "GERENTENOMBRE",
        "UBICACION",
        "EDOUBICACION",
        "JEFEDEPERSONAL",
        "NUMEROJEFE",
        "CODJEFE",
        "CIA",
        "CIASTR",
        "CC",
        "ORDENINTERNA",
        "CCOPERATIVO",
        "EMAIL",
        "USERID",
        "USERIDSAP",
        "RAZON SOCIAL HC",
        "UBICACIÓN HC",
        "ESTADO UBICACIÓN HC",
        "ASESOR RRHH HC",
        "FrecuenciaPago",
        "Importe",
        "ImporteTotal",
    ])
    mapped_columns = classifier.map_dataframe_columns(df)
    mapped = {
        column["source_column_name"]: column["canonical_field_name"]
        for column in mapped_columns
    }
    expected = {
        "NUMERO": "employee_number",
        "NOMBRE": "full_name",
        "CODPOS": "position_code",
        "CVEPTO": "job_code",
        "DESCRIPCIONPUESTO": "position",
        "VICEPRESIDENCIA": "vp_hc",
        "REGIONAREA": "area",
        "GERENTENOMBRE": "manager",
        "UBICACION": "location",
        "EDOUBICACION": "location_state",
        "JEFEDEPERSONAL": "personnel_lead",
        "NUMEROJEFE": "manager_number",
        "CODJEFE": "manager_code",
        "CIA": "company_code",
        "CIASTR": "company",
        "CC": "cc_hc",
        "ORDENINTERNA": "oi_hc",
        "CCOPERATIVO": "cc_hc",
        "EMAIL": "email",
        "USERID": "user_id",
        "USERIDSAP": "sap_user_id",
        "RAZON SOCIAL HC": "company",
        "UBICACIÓN HC": "location",
        "ESTADO UBICACIÓN HC": "location_state",
        "ASESOR RRHH HC": "personnel_lead",
        "FrecuenciaPago": "payment_frequency",
        "Importe": "salary",
        "ImporteTotal": "salary",
    }

    for source_column, expected_field in expected.items():
        assert_equal(mapped.get(source_column), expected_field, f"{source_column} alias")


def check_matching_engine(matching_engine):
    print_section("Matching Engine V1")

    assert_equal(matching_engine.normalize_name("GOMEZ LOPEZ, BRYAN"), "BRYAN GOMEZ LOPEZ", "comma name normalization")
    assert_equal(matching_engine.normalize_value("  fake.email @example.com ", "email"), "fake.email@example.com", "email normalization")
    assert_equal(matching_engine.normalize_value("$8,800.00", "salary"), "8800.00", "currency normalization")
    assert_equal(matching_engine.normalize_date("31/12/2026"), "2026-12-31", "date normalization")
    assert_equal(matching_engine.normalize_value("N/A"), None, "empty value normalization")

    source = matching_engine.build_match_profile({
        "NumEmpleado": " 1001 ",
        "CURP": "GOBB010101HNLXXX01",
        "RFC": "GOBB010101ABC",
        "EMAIL": " fake.intern@example.com ",
        "NOMBRE": "GOMEZ LOPEZ, BRYAN",
        "FechadeIngreso": "01/01/2026",
        "FechaContratoVence": "31/12/2026",
        "JefeInmediato": "Fake Manager",
        "CC HC": "8800",
        "OI HC": "OI-123",
    })
    candidates = [
        {
            "intern_id": "INT-1001",
            "NumEmpleado": "1001",
            "CURP": "GOBB010101HNLXXX01",
            "RFC": "GOBB010101ABC",
            "EMAIL": "fake.intern@example.com",
            "NombreCompleto": "Bryan Gomez Lopez",
        }
    ]
    high_match = matching_engine.resolve_best_match(source, candidates, entity_type="intern")
    assert_equal(high_match["match_confidence"], "HIGH", "strong ID match confidence")
    assert_equal(high_match["matched_entity_id"], "INT-1001", "strong ID matched entity")
    assert_equal(high_match["needs_review"], False, "HIGH match does not need review")

    medium_source = matching_engine.build_match_profile({
        "NombreCompleto": "Ana Fake Test",
        "FechadeIngreso": "2026-01-01",
        "FechaContratoVence": "2026-12-31",
        "JefeInmediato": "Manager Uno",
        "CC HC": "CC-001",
        "OI HC": "OI-001",
    })
    medium_candidates = [{
        "intern_id": "INT-MEDIUM",
        "NombreCompleto": "ANA FAKE TEST",
        "FechadeIngreso": "01/01/2026",
        "FechaContratoVence": "31/12/2026",
        "JefeInmediato": "Manager Uno",
        "CC HC": "CC-001",
        "OI HC": "OI-001",
    }]
    medium_match = matching_engine.resolve_best_match(medium_source, medium_candidates, entity_type="intern")
    assert_equal(medium_match["match_confidence"], "MEDIUM", "secondary-only match confidence")
    assert_equal(medium_match["needs_review"], True, "MEDIUM match needs review")

    low_match = matching_engine.resolve_best_match(
        matching_engine.build_match_profile({"NombreCompleto": "No Match"}),
        [{"intern_id": "INT-OTHER", "NombreCompleto": "Different Person"}],
        entity_type="intern",
    )
    assert_equal(low_match["match_confidence"], "LOW", "low/unmatched confidence")
    assert_equal(low_match["matched_entity_id"], None, "low/unmatched entity")

    conflict_source = matching_engine.build_match_profile({
        "CURP": "GOBB010101HNLXXX01",
        "RFC": "GOBB010101ABC",
        "EMAIL": "fake.intern@example.com",
        "NumEmpleado": "1001",
        "NombreCompleto": "Bryan Gomez Lopez",
    })
    conflict_candidates = [{
        "intern_id": "INT-CONFLICT",
        "CURP": "GOBB010101HNLXXX01",
        "RFC": "DIFFERENT123",
        "EMAIL": "fake.intern@example.com",
        "NumEmpleado": "9999",
        "NombreCompleto": "Bryan Gomez Lopez",
    }]
    conflict_match = matching_engine.resolve_best_match(conflict_source, conflict_candidates, entity_type="intern")
    assert_equal(conflict_match["match_confidence"], "CONFLICT", "conflict confidence")
    assert_true(conflict_match["conflict_reason"], "conflict reason exists")


def check_org_relationship_enrichment(pipeline_service):
    print_section("CEMEX Org Relationship Enrichment")

    class FakeCursor:
        def __init__(self):
            self.results = []
            self.intern_rows = [{
                "jefe_inmediato": "Manager Uno",
                "vp_hc": "VP Central",
                "cc_hc": "3024178716",
                "oi_hc": "88001234",
                "cia_hc": "7180",
            }]
            self.manager_rows = [{
                "jefe_key": pipeline_service.manager_key("Manager Uno"),
                "jefe_directo": "Manager Uno",
                "vp": "VP Central",
                "cc": "3024178716",
                "oi": "88001234",
                "compania": "7180",
            }]

        def execute(self, sql, *params):
            if "dim_manager_assignments" in sql and "SELECT CAST" in sql:
                target = next(
                    col for col in ["vp", "cc", "oi", "compania"]
                    if f"CAST({col} AS" in sql
                )
                keys = set(params)
                counts = {}
                for row in self.manager_rows:
                    if row["jefe_key"] in keys or pipeline_service.org_key(row["jefe_directo"]) in keys:
                        value = row.get(target)
                        if value:
                            counts[value] = counts.get(value, 0) + 1
                self.results = [(value, count) for value, count in counts.items()]
                return self

            if "FROM dbo.dim_interns" in sql:
                select_sql, _, where_sql = sql.partition("FROM dbo.dim_interns")
                target = next(
                    col for col in ["jefe_inmediato", "vp_hc", "cc_hc", "oi_hc", "cia_hc"]
                    if f"CAST({col} AS" in select_sql
                )
                source = next(
                    col for col in ["jefe_inmediato", "vp_hc", "cc_hc", "oi_hc", "cia_hc"]
                    if f"CAST({col} AS" in where_sql and col != target
                )
                keys = set(params)
                counts = {}
                for row in self.intern_rows:
                    if pipeline_service.org_key(row.get(source)) in keys:
                        value = row.get(target)
                        if value:
                            counts[value] = counts.get(value, 0) + 1
                self.results = [(value, count) for value, count in counts.items()]
                return self

            self.results = []
            return self

        def fetchall(self):
            return self.results

    cursor = FakeCursor()
    manager_enriched = pipeline_service.enrich_org_fields(cursor, {
        "JefeInmediato": "Manager Uno",
        "VP HC": "",
        "CC HC": "",
        "OI HC": "",
        "CIA HC": "",
    })
    assert_equal(manager_enriched["VP HC"], "VP Central", "JefeInmediato -> VP HC")
    assert_equal(manager_enriched["CC HC"], "3024178716", "JefeInmediato -> CC HC")
    assert_equal(manager_enriched["OI HC"], "88001234", "JefeInmediato -> OI HC")
    assert_equal(manager_enriched["CIA HC"], "7180", "JefeInmediato -> CIA HC")

    oi_enriched = pipeline_service.enrich_org_fields(cursor, {
        "OI HC": "88001234.0",
        "VP HC": "",
        "CC HC": "",
        "CIA HC": "",
    })
    assert_equal(oi_enriched["OI HC"], "88001234", "OI HC numeric normalization")
    assert_equal(oi_enriched["VP HC"], "VP Central", "OI HC -> VP HC")
    assert_equal(oi_enriched["CC HC"], "3024178716", "OI HC -> CC HC")
    assert_equal(oi_enriched["CIA HC"], "7180", "OI HC -> CIA HC")


def check_sql_views_if_requested():
    if os.getenv("SMOKE_CHECK_SQL_VIEWS", "").strip().lower() not in {"1", "true", "yes"}:
        print("\nSQL view check skipped. Set SMOKE_CHECK_SQL_VIEWS=1 to run a read-only Azure SQL check.")
        return

    print_section("SQL Views")
    azure_clients = require_import("azure_clients")
    expected_views = [
        "vw_pipeline_summary",
        "vw_pipeline_files",
        "vw_validation_errors",
        "vw_interns_current",
        "vw_canonical_interns_current",
        "vw_canonical_intern_documents",
        "vw_canonical_document_types",
        "vw_canonical_org_assignments",
        "vw_canonical_requisitions",
        "vw_canonical_pipeline_runs",
        "vw_schema_consolidation_recommendations",
        "vw_business_validation_exceptions",
        "vw_requisitions_status",
        "vw_communications_status",
        "vw_hr_actions_today",
        "vw_powerbi_vacantes",
        "vw_powerbi_costos_practicantes",
        "vw_powerbi_expired_active_contracts",
        "vw_powerbi_inactive_interns",
        "vw_powerbi_vp_capacity",
        "vw_powerbi_dashboard_kpis",
        "vw_powerbi_vp_summary",
        "vw_powerbi_location_summary",
        "vw_powerbi_contract_risk",
        "vw_powerbi_document_status",
        "vw_powerbi_document_summary",
        "vw_powerbi_hr_action_queue",
    ]

    conn = azure_clients.get_sql_connection()
    try:
        cursor = conn.cursor()
        for view_name in expected_views:
            cursor.execute(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.VIEWS
                WHERE TABLE_SCHEMA = 'dbo'
                  AND TABLE_NAME = ?
                """,
                view_name,
            )
            assert_true(cursor.fetchone(), f"dbo.{view_name} exists")
    finally:
        conn.close()


def main():
    print("Fake-data-only smoke test. This does not write to Azure Blob or Azure SQL.")
    modules = check_imports()
    check_entrypoint_imports()
    check_email_mode_default(modules["app_config"])
    check_classifier_routes(
        classifier=modules["flexible_file_classifier"],
        lifecycle=modules["lifecycle_requirements"],
        pandas_module=modules["pandas"],
    )
    check_corporate_column_aliases(
        classifier=modules["flexible_file_classifier"],
        pandas_module=modules["pandas"],
    )
    check_matching_engine(modules["matching_engine"])
    check_org_relationship_enrichment(modules["pipeline_service"])
    check_sql_views_if_requested()
    print("\nSmoke test passed.")


if __name__ == "__main__":
    main()
