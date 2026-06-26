"""
Local end-to-end test driver. Processes recent emails (today) that carry a document
attachment, directly through the onboarding/document pipelines — no blob, no Function
App. Dedups by UID (read-state-independent, since Gmail auto-reads self-mail). Parses
the email body and evaluates pack-1 completeness after a candidate batch.

Run with SEND_EMAILS=true to actually email. State: data/test_processed_uids.txt.
"""

import os
import sys
import json
import email
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

import intake_gmail_attachments as intake
import onboarding_pipeline as ob
import document_pipeline as dp

DL = "data/test_intake"
STATE = "data/test_processed_uids.txt"
CANDIDATE_DOC_TYPES = {"curp", "constancia", "identificacion", "comprobante_domicilio", "foto", "acta"}
DOC_EXTS = (".docx", ".xlsx", ".pdf", ".png", ".jpg", ".jpeg")


def route(local_path, filename, meta):
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".docx", ".xlsx"):
        return ob.process_onboarding_file(local_path, filename, meta)
    if ext in (".pdf", ".png", ".jpg", ".jpeg"):
        return dp.process_document(local_path, filename, meta)
    return {"status": "skipped_unsupported", "file": filename}


def _processed():
    return set(open(STATE).read().split()) if os.path.exists(STATE) else set()


def _mark(uid):
    with open(STATE, "a") as f:
        f.write(uid + "\n")


def run():
    os.makedirs(DL, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    done = _processed()
    mail = intake.connect_imap()
    mail.select("INBOX")
    since = datetime.date.today().strftime("%d-%b-%Y")
    status, data = mail.uid("search", None, "SINCE", since)   # UIDs are stable, sequence numbers are not
    ids = [i.decode() for i in (data[0].split() if status == "OK" and data and data[0] else [])]
    todo = [i for i in ids if i not in done]
    print(f"Recent emails today: {len(ids)} | unprocessed: {len(todo)}")

    for uid in todo:
        _, md = mail.uid("fetch", uid, "(RFC822)")
        msg = email.message_from_bytes(md[0][1])
        subject = intake.decode_email_header(msg.get("Subject"))
        sender = intake.decode_email_header(msg.get("From"))
        # Skip the system's own outbound mail (routed to this same inbox) to avoid a loop.
        if (subject or "").strip().startswith("[DEV]"):
            _mark(uid)
            continue
        att_parts = [p for p in msg.walk()
                     if "attachment" in str(p.get("Content-Disposition") or "").lower()
                     and intake.decode_email_header(p.get_filename() or "").lower().endswith(DOC_EXTS)]
        if not att_parts:
            _mark(uid)
            continue

        sender_email, reqid = intake.parse_sender_and_reqid(sender, subject)
        body_fields = intake.parse_intern_email_body(intake.get_email_body(msg))
        meta_base = {"sender_email": sender_email, "requisition_id": reqid or None,
                     "body_fields": json.dumps(body_fields) if body_fields else ""}
        print(f"\n========== EMAIL uid={uid} ==========")
        print(f"from={sender_email} | subject={subject!r} | reqid={reqid or '-'} | body_fields={list(body_fields)}")

        saved = []
        for part in att_parts:
            fn = intake.decode_email_header(part.get_filename() or "")
            lp = os.path.join(DL, fn.replace("/", "_"))
            with open(lp, "wb") as fh:
                fh.write(part.get_payload(decode=True))
            saved.append((lp, fn))

        # Pass 1: alta/onboarding files (.xlsx/.docx) establish the candidate.
        intern_id, results = None, []
        for lp, fn in saved:
            if os.path.splitext(fn)[1].lower() in (".xlsx", ".docx"):
                res = route(lp, fn, {**meta_base, "source_blob": lp})
                print(f"  • {fn} → {res}")
                results.append(res)
                if isinstance(res, dict) and res.get("intern_id"):
                    intern_id = res["intern_id"]
        # Pass 2: documents — all attachments in one email belong to that candidate.
        meta_docs = {**meta_base}
        if intern_id:
            meta_docs["intern_id"] = intern_id
        for lp, fn in saved:
            if os.path.splitext(fn)[1].lower() in (".pdf", ".png", ".jpg", ".jpeg"):
                res = dp.process_document(lp, fn, {**meta_docs, "source_blob": lp})
                print(f"  • {fn} → {res}")
                results.append(res)
                if isinstance(res, dict) and res.get("intern_id") and not intern_id:
                    intern_id = res["intern_id"]

        pack1_interns = {intern_id} if intern_id else set()
        for r in results:
            if isinstance(r, dict) and r.get("intern_id"):
                pack1_interns.add(r["intern_id"])
        pack1_interns.discard(None)
        for iid in pack1_interns:
            ev = dp.check_candidate_documents_complete(iid, sender_email=sender_email, notify_incomplete=True)
            print(f"  PACK-1 EVAL {iid}: {ev.get('status')} {ev.get('missing') or ''} {ev.get('problems') or ''}")

        _mark(uid)
    mail.logout()
    print("\nDone.")


if __name__ == "__main__":
    run()
