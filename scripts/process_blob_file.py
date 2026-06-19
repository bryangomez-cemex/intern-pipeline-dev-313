import os
import sys

from dotenv import load_dotenv


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from pipeline_service import process_next_blob


load_dotenv()


def main():
    run_type = os.getenv("PIPELINE_RUN_TYPE", "manual")
    return process_next_blob(run_type=run_type)


if __name__ == "__main__":
    main()
