"""
Document pipeline (stages C–E): candidate document validation + the convenio round.

Classifies each incoming document by filename/content, matches it to a candidate,
extracts text, cross-checks identity, tracks the document set in
fact_intern_documents, and drives the convenio exchange. PDFs with no text layer
(scanned CURP / passport) are validated by presence + identity, since the CURP
value itself already comes from the alta.
"""

import os
import re
import sys
import json
import uuid
import unicodedata

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import azure_clients
import onboarding_pipeline as ob

load_dotenv()

# Required candidate document set (Paquete 1). Acta de nacimiento is optional.
REQUIRED_CANDIDATE_DOCS = ["alta", "curp", "constancia", "identificacion", "comprobante_domicilio"]

# Filename keywords, most specific first.
FILENAME_KEYWORDS = [
    ("nda", ["confidencialidad", "acuerdo", "nda"]),
    ("convenio", ["convenio"]),
    ("curp", ["curp"]),
    ("constancia", ["enrollment", "constancia", "kardex", "certificate", "estudios", "escolar"]),
    ("comprobante_domicilio", ["comprobante de domicilio", "domicilio", "recibo", "luz", "agua", "telmex", "cfe"]),
    ("identificacion", ["pasaporte", "passport", "ine", "identificacion", "credencial"]),
    ("acta", ["acta", "nacimiento"]),
    ("foto", ["foto", "fotografia", "photo"]),
]
CONTENT_KEYWORDS = [
    ("nda", ["acuerdo de confidencialidad"]),
    ("convenio", ["convenio", "escuela-empresa", "practicas profesionales", "prácticas profesionales"]),
    ("constancia", ["clearinghouse", "enrollment", "constancia de estudios"]),
    ("comprobante_domicilio", ["comprobante de domicilio", "domicilio", "recibo", "codigo postal", "código postal"]),
    ("curp", ["clave unica", "curp"]),
]


def _norm(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def ocr_text(local_path):
    """OCR a scanned PDF or image with Azure AI Document Intelligence (prebuilt-read).
    Works for any format the service supports; returns the recognized text, or '' if
    not configured / on error. Cloud call, so it runs in local, CI, and the Function App."""
    endpoint = os.getenv("DOC_INTEL_ENDPOINT")
    key = os.getenv("DOC_INTEL_KEY")
    if not endpoint or not key:
        return ""
    try:
        import time
        import requests
        url = endpoint.rstrip("/") + "/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31"
        with open(local_path, "rb") as fh:
            data = fh.read()
        resp = requests.post(url, headers={"Ocp-Apim-Subscription-Key": key,
                                           "Content-Type": "application/octet-stream"},
                             data=data, timeout=60)
        if resp.status_code not in (200, 202):
            print(f"OCR submit failed {resp.status_code}: {resp.text[:160]}")
            return ""
        op = resp.headers.get("Operation-Location") or resp.headers.get("operation-location")
        for _ in range(30):
            time.sleep(2)
            g = requests.get(op, headers={"Ocp-Apim-Subscription-Key": key}, timeout=30).json()
            status = g.get("status")
            if status == "succeeded":
                return g.get("analyzeResult", {}).get("content", "") or ""
            if status == "failed":
                print(f"OCR failed: {g}")
                return ""
    except Exception as e:
        print(f"OCR error ({local_path}): {e}")
    return ""


def extract_text(local_path, ext):
    text = ""
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            text = "\n".join((p.extract_text() or "") for p in PdfReader(local_path).pages)
        elif ext == ".docx":
            import requisition_parser
            text = "\n".join(requisition_parser.extract_paragraphs(local_path))
    except Exception as e:
        print(f"text extract note ({local_path}): {e}")
    # OCR fallback: scanned PDFs (no text layer) and images.
    if ext in (".png", ".jpg", ".jpeg") or (ext == ".pdf" and len(text.strip()) < 30):
        ocr = ocr_text(local_path)
        if ocr:
            text = (text + "\n" + ocr).strip()
    return text


def classify_document_type(local_path, filename):
    ext = os.path.splitext(filename)[1].lower()
    nfile = _norm(filename)
    if ext in (".png", ".jpg", ".jpeg"):
        for dtype, kws in FILENAME_KEYWORDS:
            if any(k in nfile for k in kws):
                return dtype, ""
        text = extract_text(local_path, ext)
        ntext = _norm(text)
        for dtype, kws in CONTENT_KEYWORDS:
            if any(k in ntext for k in kws):
                return dtype, text
        return "other", text
    if ext in (".xlsx", ".csv"):
        return "alta", ""
    text = extract_text(local_path, ext)
    ntext = _norm(text)
    for dtype, kws in FILENAME_KEYWORDS:
        if any(k in nfile for k in kws):
            return dtype, text
    for dtype, kws in CONTENT_KEYWORDS:
        if any(k in ntext for k in kws):
            return dtype, text
    return "other", text


def _name_tokens(full_name):
    toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", _norm(full_name)).split() if len(t) > 2]
    return set(toks)


def _identity_match(candidate_name, filename, text):
    """True/False when the name can be checked; None when the document carries no
    readable name (scanned PDF, image, spreadsheet) — those are verified by presence
    only, not flagged as a mismatch."""
    toks = _name_tokens(candidate_name)
    if not toks:
        return None
    if text and len(text.strip()) > 100:
        hits = sum(1 for t in toks if t in _norm(text))
        return hits >= 2  # readable content: verify the name appears
    fhits = sum(1 for t in toks if t in _norm(filename))
    return True if fhits >= 2 else None  # otherwise filename, else cannot verify


def _match_candidate(cur, meta, candidate_name_hint=None):
    intern_id = (meta or {}).get("intern_id")
    if intern_id:
        return intern_id
    req_id = ob.extract_requisition_id(
        (meta or {}).get("requisition_id"),
        (meta or {}).get("email_subject"),
        (meta or {}).get("source_blob"),
        candidate_name_hint,
    )
    if req_id:
        cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE requisition_id=?", req_id)
        r = cur.fetchone()
        if r:
            return r[0]
    sender = (meta or {}).get("sender_email")
    if sender:
        cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE LOWER(email_personal)=LOWER(?)", sender)
        r = cur.fetchone()
        if r:
            return r[0]
    if candidate_name_hint:
        toks = _name_tokens(candidate_name_hint)
        cur.execute("SELECT intern_id, nombre_completo FROM dim_interns")
        for iid, nc in cur.fetchall():
            if nc and len(_name_tokens(nc) & toks) >= 2:
                return iid
    return None


# ============================================================
# Stage C — candidate documents
# ============================================================

def process_candidate_document(local_path, filename, meta=None):
    meta = meta or {}
    ext = os.path.splitext(filename)[1].lower()
    dtype, text = classify_document_type(local_path, filename)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        intern_id = _match_candidate(cur, meta, candidate_name_hint=filename)

        # Identify the owner from the document CONTENT (not by forcing the name into
        # the file): read the CURP from the document and, if we still don't know whose
        # it is, match the candidate by that CURP.
        extracted = {}
        if dtype == "curp" and text:
            m = re.search(r"[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]", text.upper().replace(" ", ""))
            if m:
                extracted["curp"] = m.group(0)
        if not intern_id and extracted.get("curp"):
            cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE UPPER(curp) = ?", extracted["curp"])
            rr = cur.fetchone()
            if rr:
                intern_id = rr[0]

        cand_name, alta_curp = None, ""
        if intern_id:
            cur.execute("SELECT nombre_completo, curp FROM dim_interns WHERE intern_id=?", intern_id)
            row = cur.fetchone()
            if row:
                cand_name = row[0]
                alta_curp = (row[1] or "").upper() if row[1] else ""

        # Name presence is informational only (stored as name_match), never a blocker.
        name_match = _identity_match(cand_name, filename, text) if cand_name else None

        problems = []
        # A CURP that contradicts the alta is still a real problem.
        if extracted.get("curp") and alta_curp and alta_curp != extracted["curp"]:
            problems.append(f"la CURP del documento ({extracted['curp']}) no coincide con el alta ({alta_curp})")
        if dtype == "constancia" and text:
            m = re.search(r"(anticipated graduation|graduation date|fecha de graduaci[oó]n)[:\s]*([A-Za-z0-9 ,/]+)", text, re.I)
            if m:
                extracted["graduacion"] = m.group(2).strip()[:40]
                if intern_id:
                    cur.execute("UPDATE dim_interns SET fecha_graduacion = COALESCE(fecha_graduacion, ?) WHERE intern_id=?",
                                extracted["graduacion"], intern_id)

        doc_id = "DOC-" + str(uuid.uuid4())[:8]
        cur.execute(
            """INSERT INTO fact_intern_documents
               (document_id, intern_id, stage, document_type, file_name, blob_path,
                name_match, extracted, status, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            doc_id, intern_id, "candidate_docs", dtype, filename, meta.get("source_blob"),
            (1 if name_match else 0) if name_match is not None else None,
            json.dumps(extracted) if extracted else None,
            "problem" if problems else "received", "; ".join(problems) if problems else None,
        )
        conn.commit()
        print(f"  doc: {filename} → type={dtype} intern={intern_id} name_match={name_match} extracted={extracted}")
        return {"document_id": doc_id, "intern_id": intern_id, "document_type": dtype,
                "name_match": name_match, "extracted": extracted, "problems": problems}
    finally:
        cur.close(); conn.close()


def check_candidate_documents_complete(intern_id, sender_email=None, notify_incomplete=True):
    """Paquete 1 completeness + identity check. On complete → confirm to the candidate
    (once). On incomplete → return to sender with the reasons, but only when
    notify_incomplete=True (so per-document auto-checks during collection stay quiet)."""
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT nombre_completo, email_personal, documents_status FROM dim_interns WHERE intern_id=?", intern_id)
        row = cur.fetchone()
        cand_name, cand_email, prev_status = (row[0], row[1], row[2]) if row else (None, None, None)
        cur.execute(
            "SELECT document_type, notes FROM fact_intern_documents "
            "WHERE intern_id=? AND stage='candidate_docs'", intern_id)
        rows = cur.fetchall()
        received = {r[0] for r in rows}
        doc_problems = sorted({r[1] for r in rows if r[1]})
        missing = [d for d in REQUIRED_CANDIDATE_DOCS if d not in received]

        problems = []
        if missing:
            problems.append("faltan documentos: " + ", ".join(missing))
        problems.extend(doc_problems)

        if problems:
            cur.execute("UPDATE dim_interns SET documents_status='incomplete' WHERE intern_id=?", intern_id)
            conn.commit()
            if notify_incomplete:
                ob._return_to_sender(sender_email or cand_email, "documentos del practicante (Paquete 1)", problems)
            return {"status": "incomplete", "intern_id": intern_id, "missing": missing, "problems": doc_problems}

        cur.execute("UPDATE dim_interns SET documents_status='complete' WHERE intern_id=?", intern_id)
        conn.commit()
        if prev_status != "complete":  # confirm only on transition
            ob.send_email(cand_email or "candidate",
                          "Documentos recibidos – Summer Internship Program",
                          f"Hola, recibimos y validamos tu expediente completo ({', '.join(sorted(received))}). "
                          "En breve te enviaremos tu convenio y Acuerdo de Confidencialidad para firma.")
        return {"status": "complete", "intern_id": intern_id, "received": sorted(received)}
    finally:
        cur.close(); conn.close()


# ============================================================
# Stages D/E — convenio round
# ============================================================

def process_convenio_doc(local_path, filename, meta=None):
    """HR sends convenio / póliza / Acuerdo de Confidencialidad → store, link to the
    candidate; once present, forward to the new hire (Welcome 2) with attachments."""
    meta = meta or {}
    dtype, text = classify_document_type(local_path, filename)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        intern_id = _match_candidate(cur, meta, candidate_name_hint=filename)
        doc_id = "DOC-" + str(uuid.uuid4())[:8]
        cur.execute(
            """INSERT INTO fact_intern_documents
               (document_id, intern_id, stage, document_type, file_name, blob_path, status)
               VALUES (?,?,?,?,?,?, 'received')""",
            doc_id, intern_id, "convenio", dtype, filename, meta.get("source_blob") or local_path)
        conn.commit()
        print(f"  convenio doc: {filename} → type={dtype} intern={intern_id}")
        return {"document_id": doc_id, "intern_id": intern_id, "document_type": dtype}
    finally:
        cur.close(); conn.close()


def forward_convenio_to_candidate(intern_id):
    """Once HR's convenio + NDA are in, forward them to the new hire (Welcome 2)."""
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT nombre, email_personal, documents_status FROM dim_interns WHERE intern_id=?", intern_id)
        row = cur.fetchone()
        name, email, docs_status = (row[0], row[1], row[2]) if row else (None, None, None)
        # step 9: only forward pack 2 if Paquete 1 passed everything
        if docs_status != "complete":
            return {"status": "waiting_pack1_complete", "documents_status": docs_status}
        cur.execute(
            "SELECT document_type, file_name, blob_path FROM fact_intern_documents "
            "WHERE intern_id=? AND stage='convenio'", intern_id)
        docs = cur.fetchall()
        have = {d[0] for d in docs}
        if not ({"convenio", "nda"} <= have):
            return {"status": "waiting_convenio_docs", "have": sorted(have)}
        attachments, temps = [], []
        for d in docs:
            lp, is_temp = _localize(d[2])
            if lp:
                attachments.append(lp)
                if is_temp:
                    temps.append(lp)
        try:
            ob.send_email(email or "candidate",
                          "¡Te damos la bienvenida a Cemex! Documentos – Summer Internship Program",
                          f"Hola {name}, adjunto encontrarás el convenio de prácticas y la carta de Acuerdo de "
                          "Confidencialidad. Por favor revísalos, fírmalos (digital o impreso/escaneado) y "
                          "envíalos de regreso en PDF con el formato Nombre_Apellido_NombreDocumento.",
                          attachments=attachments)
        finally:
            for t in temps:
                try:
                    os.unlink(t)
                except OSError:
                    pass
        cur.execute("UPDATE dim_interns SET convenio_status='sent_to_candidate' WHERE intern_id=?", intern_id)
        conn.commit()
        return {"status": "convenio_sent", "intern_id": intern_id, "attachments": len(attachments)}
    finally:
        cur.close(); conn.close()


def _localize(path):
    """Return a readable local path: use it if it exists, else download the blob
    (raw-uploads) to a temp file. Returns (local_path, is_temp)."""
    if path and os.path.exists(path):
        return path, False
    try:
        import tempfile
        from app_config import CONFIG
        client = azure_clients.get_blob_service_client().get_blob_client(
            container=CONFIG.raw_uploads_container, blob=path)
        tmp = tempfile.NamedTemporaryFile(suffix=os.path.splitext(path or "")[1], delete=False)
        tmp.write(client.download_blob().readall()); tmp.close()
        return tmp.name, True
    except Exception as e:
        print(f"localize failed for {path}: {e}")
        return None, False


def process_document(local_path, filename, meta=None):
    """Unified entry used by the router for PDFs/images/NDA docx. Decides the stage:
    candidate documents (C), HR convenio docs (D), or signed returns (E). Returns a
    result dict if it handled the file, else None to fall back to the old pipeline."""
    meta = meta or {}
    dtype, _ = classify_document_type(local_path, filename)
    if dtype in ("alta", "other"):
        return None  # alta handled by onboarding; unknown → old pipeline

    sender = meta.get("sender_email")
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        intern_id = _match_candidate(cur, meta, candidate_name_hint=filename)
        convenio_status = None
        from_candidate = False
        if intern_id:
            cur.execute("SELECT email_personal, convenio_status FROM dim_interns WHERE intern_id=?", intern_id)
            r = cur.fetchone()
            if r:
                from_candidate = bool(sender and r[0] and sender.lower() == str(r[0]).lower())
                convenio_status = r[1]
    finally:
        cur.close(); conn.close()

    m = {**meta, "intern_id": intern_id}
    if dtype in ("curp", "constancia", "identificacion", "comprobante_domicilio", "foto", "acta"):
        res = process_candidate_document(local_path, filename, m)
        if intern_id:
            check_candidate_documents_complete(intern_id, sender_email=sender, notify_incomplete=False)
        return res
    if dtype in ("convenio", "nda"):
        # candidate returning a signed doc vs HR sending the originals
        if convenio_status == "sent_to_candidate" or from_candidate:
            return process_signed_doc(local_path, filename, m)
        res = process_convenio_doc(local_path, filename, m)
        if intern_id:
            forward_convenio_to_candidate(intern_id)
        return res
    return None


def process_signed_doc(local_path, filename, meta=None):
    """New hire returns the signed convenio / NDA. Validate naming + presence; when
    both are back, mark the round complete and notify HR."""
    meta = meta or {}
    dtype, text = classify_document_type(local_path, filename)
    naming_ok = bool(re.match(r"^[A-Za-zÁÉÍÓÚñÑ]+[_ ][A-Za-zÁÉÍÓÚñÑ]+[_ ].+", filename))
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        intern_id = _match_candidate(cur, meta, candidate_name_hint=filename)
        doc_id = "DOC-" + str(uuid.uuid4())[:8]
        cur.execute(
            """INSERT INTO fact_intern_documents
               (document_id, intern_id, stage, document_type, file_name, blob_path, status, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            doc_id, intern_id, "signed", dtype, filename, meta.get("source_blob"),
            "received", None if naming_ok else "nombre de archivo no sigue Nombre_Apellido_Documento")
        conn.commit()
        # check completeness of the signed set
        cur.execute("SELECT document_type FROM fact_intern_documents WHERE intern_id=? AND stage='signed'", intern_id)
        have = {r[0] for r in cur.fetchall()}
        if {"convenio", "nda"} <= have:
            cur.execute("UPDATE dim_interns SET convenio_status='signed_complete' WHERE intern_id=?", intern_id)
            conn.commit()
            cur.execute("SELECT nombre_completo FROM dim_interns WHERE intern_id=?", intern_id)
            nm = cur.fetchone()
            ob.send_email((ob._resolve_recipients(cur)).get("HR") or "hr",
                          "Convenio firmado recibido",
                          f"El practicante {nm[0] if nm else intern_id} devolvió el convenio y el Acuerdo de "
                          f"Confidencialidad firmados. Proceso de documentos completo.")
            # step 12: everything complete → Coparmex package + final emails (HR, new hire, Coparmex)
            final = ob.finalize_onboarding(intern_id)
            return {"document_id": doc_id, "intern_id": intern_id, "status": "signed_complete",
                    "naming_ok": naming_ok, "finalize": final.get("status")}
        return {"document_id": doc_id, "intern_id": intern_id, "status": "received", "naming_ok": naming_ok}
    finally:
        cur.close(); conn.close()
