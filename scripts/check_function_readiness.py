import importlib
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FUNCTION_APP_DIR = REPO_ROOT / "azure_function_app"
FUNCTION_SCRIPTS_DIR = FUNCTION_APP_DIR / "scripts"
ROOT_SCRIPTS_DIR = REPO_ROOT / "scripts"

REQUIRED_FILES = [
    FUNCTION_APP_DIR / "function_app.py",
    FUNCTION_APP_DIR / "host.json",
    FUNCTION_APP_DIR / "requirements.txt",
    FUNCTION_APP_DIR / "local.settings.example.json",
    FUNCTION_APP_DIR / "README.md",
    FUNCTION_SCRIPTS_DIR / "pipeline_service.py",
    FUNCTION_SCRIPTS_DIR / "app_config.py",
    FUNCTION_SCRIPTS_DIR / "azure_clients.py",
    FUNCTION_SCRIPTS_DIR / "document_pipeline.py",
    FUNCTION_SCRIPTS_DIR / "flexible_file_classifier.py",
    FUNCTION_SCRIPTS_DIR / "lifecycle_requirements.py",
    FUNCTION_SCRIPTS_DIR / "matching_engine.py",
    FUNCTION_SCRIPTS_DIR / "onboarding_pipeline.py",
    FUNCTION_SCRIPTS_DIR / "communication_packager.py",
    FUNCTION_SCRIPTS_DIR / "requisition_parser.py",
    REPO_ROOT / "requirements.txt",
    ROOT_SCRIPTS_DIR / "deployment_readiness_e2e.py",
]

REQUIRED_ENV_VARS = [
    "AZURE_STORAGE_CONNECTION_STRING",
    "RAW_UPLOADS_CONTAINER",
    "ERROR_REPORTS_CONTAINER",
    "ARCHIVE_CONTAINER",
    "AZURE_SQL_SERVER",
    "AZURE_SQL_DATABASE",
    "AZURE_SQL_AUTH_MODE",
    "EMAIL_MODE",
    "DEV_EMAIL_OVERRIDE",
    "DOC_INTEL_ENDPOINT",
    "DOC_INTEL_KEY",
]

REQUIRED_PIPELINE_FUNCTIONS = [
    "process_blob_by_name",
    "process_next_blob",
    "process_all_pending_blobs",
    "run_pipeline_for_uploaded_file",
]


def check_required_files():
    missing = [path for path in REQUIRED_FILES if not path.exists()]

    if missing:
        print("Missing required files:")
        for path in missing:
            print(f"- {path.relative_to(REPO_ROOT)}")
        return False

    print("Required files: OK")
    return True


def check_imports():
    sys.path.insert(0, str(FUNCTION_SCRIPTS_DIR))
    sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

    modules = [
        "pipeline_service",
        "app_config",
        "azure_clients",
        "document_pipeline",
        "flexible_file_classifier",
        "lifecycle_requirements",
        "matching_engine",
        "onboarding_pipeline",
        "communication_packager",
        "requisition_parser",
    ]

    try:
        for module_name in modules:
            importlib.import_module(module_name)
            print(f"Import {module_name}: OK")

        pipeline_service = importlib.import_module("pipeline_service")

        for function_name in REQUIRED_PIPELINE_FUNCTIONS:
            if not hasattr(pipeline_service, function_name):
                raise AttributeError(f"pipeline_service missing {function_name}")
            print(f"pipeline_service.{function_name}: OK")
    except ModuleNotFoundError as exc:
        missing_name = exc.name or "unknown"
        print(f"Import check failed. Missing dependency/module: {missing_name}")
        print("Install local dependencies with:")
        print("python3 -m pip install -r requirements.txt")
        print("For Azure Function local tests, also use:")
        print("python3 -m pip install -r azure_function_app/requirements.txt")
        return False

    return True


def check_env_vars():
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]

    if missing:
        print("Local env vars missing for a local end-to-end test:")
        for name in missing:
            print(f"- {name}")
        print("This is a warning only. No Blob or SQL connection was opened.")
        return True

    print("Local env vars: OK")
    return True


def main():
    checks = [
        check_required_files(),
        check_imports(),
        check_env_vars(),
    ]

    if not all(checks):
        raise SystemExit(1)

    print("Azure Function readiness check passed.")


if __name__ == "__main__":
    main()
