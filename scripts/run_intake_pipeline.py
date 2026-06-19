import os
import re
import subprocess
import sys


# ============================================================
# CONFIG
# ============================================================

LOCAL_INTAKE_SCRIPT = "scripts/intake_local_folder.py"
GMAIL_INTAKE_SCRIPT = "scripts/intake_gmail_attachments.py"
PIPELINE_SCRIPT = "scripts/process_blob_file.py"


# ============================================================
# HELPERS
# ============================================================

def run_script(script_path, extra_env=None):
    print("\n========================================")
    print(f"Running: {script_path}")
    print("========================================")

    env = os.environ.copy()

    if extra_env:
        env.update(extra_env)

    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True,
        env=env
    )

    print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"Script failed: {script_path}")

    return result.stdout


def get_uploaded_file_count(output):
    matches = re.findall(r"Uploaded files:\s*(\d+)", output)

    if not matches:
        return 0

    return int(matches[-1])


# ============================================================
# MAIN
# ============================================================

def run_intake_pipeline(mode="local"):
    """
    mode='local' → uses intake_files folder
    mode='gmail' → uses Gmail unread attachments
    """
    if mode == "local":
        intake_output = run_script(LOCAL_INTAKE_SCRIPT)
    elif mode == "gmail":
        intake_output = run_script(GMAIL_INTAKE_SCRIPT)
    else:
        raise ValueError("Mode must be 'local' or 'gmail'.")

    uploaded_count = get_uploaded_file_count(intake_output)

    if uploaded_count > 0:
        print("\nNew files uploaded. Running processing pipeline...")
        run_script(
            PIPELINE_SCRIPT,
            extra_env={"PIPELINE_RUN_TYPE": mode}
        )
        print("\nMVP 7C completed.")
    else:
        print("\nNo new uploaded files detected. Pipeline was not run.")


if __name__ == "__main__":
    mode = "local"

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    run_intake_pipeline(mode=mode)
