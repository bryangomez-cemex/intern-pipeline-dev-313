from pathlib import Path
from shutil import copy2


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "scripts"
FUNCTION_SCRIPTS_DIR = REPO_ROOT / "azure_function_app" / "scripts"

MODULES_TO_COPY = [
    "app_config.py",
    "azure_clients.py",
    "communication_packager.py",
    "flexible_file_classifier.py",
    "lifecycle_requirements.py",
    "matching_engine.py",
    "pipeline_service.py",
]


def sync_function_modules():
    FUNCTION_SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    copied = []
    for module_name in MODULES_TO_COPY:
        source_path = SOURCE_DIR / module_name
        target_path = FUNCTION_SCRIPTS_DIR / module_name

        if not source_path.exists():
            raise FileNotFoundError(f"Missing source module: {source_path}")

        copy2(source_path, target_path)
        copied.append(str(target_path.relative_to(REPO_ROOT)))

    return copied


if __name__ == "__main__":
    copied_modules = sync_function_modules()
    print("Synced Azure Function pipeline modules:")
    for copied_module in copied_modules:
        print(f"- {copied_module}")
