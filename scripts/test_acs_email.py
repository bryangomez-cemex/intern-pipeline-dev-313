"""
Local test for the Azure Communication Services email service.

Loads .env if present, sends to TEST_EMAIL_TO, prints the result.
Safe by default: with EMAIL_SIMULATION_MODE=true it does not send a real email.

    python scripts/test_acs_email.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import email_service


def main():
    to_email = os.getenv("TEST_EMAIL_TO") or "test@example.com"
    result = email_service.send_email(
        to_email=to_email,
        subject="ACS email service test – Intern Pipeline",
        html_body="<h3>Hello from the Intern Pipeline</h3>"
                  "<p>This is a test of the Azure Communication Services email service.</p>",
        to_name="Intern Pipeline Test",
    )
    print("EMAIL_SIMULATION_MODE:", os.getenv("EMAIL_SIMULATION_MODE", "true"))
    print("to:", to_email)
    print("result:", result)


if __name__ == "__main__":
    main()
