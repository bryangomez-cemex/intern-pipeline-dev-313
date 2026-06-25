from pathlib import Path
from shutil import copy2


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "scripts"
SOURCE_SQL_DIR = SOURCE_DIR / "sql"
FUNCTION_SCRIPTS_DIR = REPO_ROOT / "azure_function_app" / "scripts"
FUNCTION_SQL_DIR = REPO_ROOT / "azure_function_app" / "sql"

MODULES_TO_COPY = [
    "app_config.py",
    "azure_clients.py",
    "communication_packager.py",
    "document_pipeline.py",
    "flexible_file_classifier.py",
    "lifecycle_requirements.py",
    "matching_engine.py",
    "onboarding_pipeline.py",
    "pipeline_service.py",
    "requisition_parser.py",
]

SQL_SCRIPTS_TO_COPY = [
    "00_create_core_legacy_tables.sql",
    "00_create_dim_interns.sql",
    "create_full_mvp_pipeline.sql",
    "fix_file_id_source_file_id_compatibility.sql",
    "seed_pipeline_validation_rules.sql",
    "2026-06_package1_document_requirements.sql",
    "2026-06_resolve_stale_missing_items.sql",
    "add_corporate_column_aliases.sql",
    "create_matching_engine_v1.sql",
    "create_business_powerbi_views.sql",
    "2026-06_onboarding_schema.sql",
    "2026-06_schema_simplification.sql",
    "2026-06_powerbi_no_dax_views.sql",
]


def sync_function_modules():
    FUNCTION_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    FUNCTION_SQL_DIR.mkdir(parents=True, exist_ok=True)

    copied = []
    for module_name in MODULES_TO_COPY:
        source_path = SOURCE_DIR / module_name
        target_path = FUNCTION_SCRIPTS_DIR / module_name

        if not source_path.exists():
            raise FileNotFoundError(f"Missing source module: {source_path}")

        copy2(source_path, target_path)
        copied.append(str(target_path.relative_to(REPO_ROOT)))

    for script_name in SQL_SCRIPTS_TO_COPY:
        source_path = SOURCE_SQL_DIR / script_name
        target_path = FUNCTION_SQL_DIR / script_name

        if not source_path.exists():
            raise FileNotFoundError(f"Missing source SQL script: {source_path}")

        copy2(source_path, target_path)
        copied.append(str(target_path.relative_to(REPO_ROOT)))

    return copied


if __name__ == "__main__":
    copied_modules = sync_function_modules()
    print("Synced Azure Function pipeline modules:")
    for copied_module in copied_modules:
        print(f"- {copied_module}")
