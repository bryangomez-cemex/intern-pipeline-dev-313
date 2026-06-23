"""
Onboarding pipeline: requisición → Position, and candidate alta → Candidate.

Self-contained processors used by the runner and callable directly. Classifies an
incoming file, parses it with the rule-based extractors, writes the result to
Azure SQL, and sends a confirmation or a return-to-sender email (dev-safe: all mail
goes to DEV_EMAIL_OVERRIDE with the real intended recipient noted in the body).
"""

import os
import re
import sys
import uuid
import smtplib
import unicodedata
from datetime import datetime, UTC, date
from email.message import EmailMessage

import pandas as pd
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import azure_clients
import requisition_parser

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USERNAME
DEV_EMAIL_OVERRIDE = os.getenv("DEV_EMAIL_OVERRIDE")
SEND_EMAILS = os.getenv("SEND_EMAILS", "false").strip().lower() == "true"

CURP_RE = re.compile(r"^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REQ_IN_TEXT = re.compile(r"REQ-\d{4}-\d{3,}", re.IGNORECASE)


# ============================================================
# helpers
# ============================================================

def _norm(value):
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip().strip("*: ")


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _coerce_date(value):
    if value is None:
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _next_sequential_id(cursor, table, column, prefix):
    year = datetime.now(UTC).year
    cursor.execute(
        f"SELECT MAX([{column}]) FROM [{table}] WHERE [{column}] LIKE ?",
        f"{prefix}-{year}-%",
    )
    row = cursor.fetchone()
    last = row[0] if row else None
    n = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{prefix}-{year}-{n:04d}"


# ============================================================
# classification (by content, not filename)
# ============================================================

def classify_document(local_path, filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if ext == "docx":
        try:
            text = " ".join(requisition_parser.extract_paragraphs(local_path)).lower()
        except Exception:
            text = ""
        if "nombre del puesto" in text or "requisic" in text or "información de la vacante" in _norm(text):
            return "requisicion"
        return "document"
    if ext in {"xlsx", "csv"}:
        try:
            grid = pd.read_excel(local_path, header=None, nrows=20).astype(str)
            blob = " ".join(_norm(c) for c in grid.values.ravel())
        except Exception:
            blob = ""
        if "datos del practicante" in blob or "administracion de practicantes" in blob or "curp" in blob and "beneficiarios" in blob:
            return "alta_candidate"
        if "numempleado" in blob or "nombrecompleto" in blob:
            return "intern_data"
        return "other"
    if ext in {"pdf", "png", "jpg", "jpeg"}:
        return "document"
    return "other"


# ============================================================
# alta (candidate) excel parser
# ============================================================

ALTA_LABELS = {
    "nombres": "nombre", "apellido paterno": "paterno", "apellido materno": "materno",
    "sexo": "sexo", "estado civil": "estado_civil", "nacionalidad": "nacionalidad",
    "matricula": "matricula", "carrera": "carrera", "grado": "grado",
    "telefono": "telefono", "mail": "email_personal", "fecha de nacimiento": "fecha_nacimiento",
    "curp": "curp", "calle": "calle", "numero exterior": "numero_exterior",
    "colonia": "colonia", "poblacion": "poblacion", "estado": "estado_direccion",
    "codigo postal": "codigo_postal",
}


def parse_alta_excel(local_path):
    grid = pd.read_excel(local_path, header=None)
    rows = grid.values.tolist()
    fields = {}
    beneficiaries = []
    in_beneficiaries = False

    for r in rows:
        cells = [_clean(c) for c in r]
        norms = [_norm(c) for c in r]

        if any(n == "beneficiarios" for n in norms):
            in_beneficiaries = True
            continue

        # label-in-cell, value-in-next-cell (scan the row)
        for i, n in enumerate(norms):
            if n in ALTA_LABELS and i + 1 < len(cells):
                field = ALTA_LABELS[n]
                value = cells[i + 1]
                if value and fields.get(field) in (None, ""):  # first occurrence wins
                    fields[field] = value

        if in_beneficiaries:
            vals = [c for c in cells if c]
            # a beneficiary data row has a name + parentesco + percentage
            if len(vals) >= 4 and _norm(vals[0]) not in ("nombres", "beneficiarios"):
                beneficiaries.append({
                    "nombre": cells[0], "paterno": cells[1] if len(cells) > 1 else None,
                    "materno": cells[2] if len(cells) > 2 else None,
                    "parentesco": cells[3] if len(cells) > 3 else None,
                    "porcentaje": str(cells[4]) if len(cells) > 4 and cells[4] else None,
                })

    if fields.get("fecha_nacimiento"):
        fields["fecha_nacimiento"] = _coerce_date(fields["fecha_nacimiento"])
    fields["nombre_completo"] = " ".join(
        x for x in [fields.get("nombre"), fields.get("paterno"), fields.get("materno")] if x
    ) or None
    return fields, beneficiaries


def validate_candidate(fields, requisicion=None):
    """Return (blocking_errors, warnings). Maps to the data-dictionary rules."""
    errors, warnings = [], []
    if not fields.get("nombre_completo"):
        errors.append("R009 · falta el nombre completo del practicante.")
    email = fields.get("email_personal")
    if not email:
        errors.append("R010 · falta el correo del practicante.")
    elif not EMAIL_RE.match(email):
        errors.append(f"R010 · el correo '{email}' no tiene formato válido.")
    curp = (fields.get("curp") or "").upper()
    if not curp:
        errors.append("CURP · falta la CURP (campo obligatorio del banco).")
    elif not CURP_RE.match(curp):
        errors.append(f"CURP · la CURP '{curp}' no tiene el formato válido de 18 caracteres.")
    if not fields.get("carrera"):
        errors.append("R003 · falta la carrera del practicante.")
    fn = fields.get("fecha_nacimiento")
    if isinstance(fn, date) and fn > date.today():
        errors.append("fecha de nacimiento · no puede ser futura.")
    if requisicion and fields.get("carrera") and requisicion.get("carrera_requerida"):
        if _norm(fields["carrera"]) != _norm(requisicion["carrera_requerida"]):
            warnings.append(
                f"carrera '{fields['carrera']}' no coincide con la requisición "
                f"('{requisicion['carrera_requerida']}')."
            )
    return errors, warnings


# ============================================================
# email (dev-safe: all mail routed to DEV_EMAIL_OVERRIDE)
# ============================================================

def send_email(intended_to, subject, body):
    target = DEV_EMAIL_OVERRIDE or intended_to
    if not SEND_EMAILS:
        print(f"[SIMULATED EMAIL] to={intended_to} (routed {target}) subj={subject}")
        return {"status": "simulated", "to": target}
    msg = EmailMessage()
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = target
    msg["Subject"] = f"[DEV] {subject}"
    msg.set_content(
        f"DEV TEST — intended recipient: {intended_to}\n"
        f"(routed to {target} for safety)\n\n{body}\n"
    )
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo(); s.starttls(); s.ehlo()
        s.login(SMTP_USERNAME, SMTP_PASSWORD)
        s.send_message(msg)
    print(f"[EMAIL SENT] to={intended_to} (routed {target}) subj={subject}")
    return {"status": "sent", "to": target}


def _return_to_sender(sender_email, what, reasons):
    body = (
        f"Tu envío ({what}) no pudo procesarse porque encontramos lo siguiente:\n\n"
        + "\n".join(f"  • {r}" for r in reasons)
        + "\n\nPor favor corrige y reenvía. Gracias."
    )
    return send_email(sender_email or "unknown-sender", f"Devolución: {what}", body)


# ============================================================
# processors
# ============================================================

def process_requisicion(local_path, meta=None):
    meta = meta or {}
    fields = requisition_parser.parse_requisition_docx(local_path)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        req_id = _next_sequential_id(cur, "dim_requisitions", "requisition_id", "REQ")
        cur.execute(
            """INSERT INTO dim_requisitions
               (requisition_id, requisition_type, process_type_id, vp, area, manager_name,
                puesto, direccion, region_area, asesor_rh, carrera_requerida, semestre_requerido,
                disponibilidad_horario, periodo_estadia, fecha_inicio_solicitada, fecha_termino_solicitada,
                descripcion_proyecto, retos, responsabilidades, entregables, habilidades,
                needs_review, parse_notes, source_container, source_blob_name, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,SYSUTCDATETIME())""",
            req_id, "Alta", "PT006", fields.get("vp"), fields.get("region_area"), fields.get("manager_name"),
            fields.get("puesto"), fields.get("direccion"), fields.get("region_area"), fields.get("asesor_rh"),
            fields.get("carrera_requerida"), fields.get("semestre_requerido"),
            fields.get("disponibilidad_horario"), fields.get("periodo_estadia"),
            fields.get("fecha_inicio_solicitada"), fields.get("fecha_termino_solicitada"),
            fields.get("descripcion_proyecto"), fields.get("retos"), fields.get("responsabilidades"),
            fields.get("entregables"), fields.get("habilidades"),
            1 if fields.get("needs_review") else 0, fields.get("parse_notes"),
            meta.get("source_container"), meta.get("source_blob"),
        )
        conn.commit()
        if fields.get("needs_review"):
            _return_to_sender(meta.get("sender_email"), f"requisición ({fields.get('puesto') or 'sin puesto'})",
                              [fields.get("parse_notes") or "faltan campos requeridos."])
        result = {"type": "requisicion", "status": "needs_review" if fields.get("needs_review") else "created",
                  "requisition_id": req_id, "puesto": fields.get("puesto")}
        print(f"REQUISICIÓN → {req_id} ({result['status']}) puesto={fields.get('puesto')}")
        return result
    finally:
        cur.close(); conn.close()


def process_candidate(local_path, meta=None):
    meta = meta or {}
    fields, beneficiaries = parse_alta_excel(local_path)
    req_id = meta.get("requisition_id")
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        requisicion = None
        if req_id:
            cur.execute("SELECT requisition_id, carrera_requerida FROM dim_requisitions WHERE requisition_id=?", req_id)
            r = cur.fetchone()
            requisicion = {"requisition_id": r[0], "carrera_requerida": r[1]} if r else None
            if not requisicion:
                req_id = None

        errors, warnings = validate_candidate(fields, requisicion)
        if not req_id:
            warnings.append("sin Position ID (REQ) — practicante no vinculado a una requisición.")

        if errors:
            _return_to_sender(meta.get("sender_email"),
                              f"alta de {fields.get('nombre_completo') or 'practicante'}", errors)
            conn.commit()
            print(f"CANDIDATE returned to sender: {len(errors)} error(s)")
            return {"type": "candidate", "status": "returned", "errors": errors}

        pra_id = _next_sequential_id(cur, "dim_interns", "intern_id", "PRA")
        cur.execute(
            """INSERT INTO dim_interns
               (intern_id, nombre, paterno, materno, nombre_completo, sexo, curp, carrera, semestre,
                universidad, email, email_personal, telefono, estado_civil, nacionalidad, matricula, grado,
                fecha_nacimiento, calle, numero_exterior, colonia, poblacion, estado_direccion, codigo_postal,
                requisition_id, status_id, candidate_source_blob, candidate_needs_review, candidate_validation_notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            pra_id, fields.get("nombre"), fields.get("paterno"), fields.get("materno"),
            fields.get("nombre_completo"), fields.get("sexo"), (fields.get("curp") or "").upper(),
            fields.get("carrera"), fields.get("semestre_requerido") or fields.get("grado"),
            None, fields.get("email_personal"), fields.get("email_personal"), fields.get("telefono"),
            fields.get("estado_civil"), fields.get("nacionalidad"), fields.get("matricula"), fields.get("grado"),
            fields.get("fecha_nacimiento"), fields.get("calle"), fields.get("numero_exterior"),
            fields.get("colonia"), fields.get("poblacion"), fields.get("estado_direccion"),
            fields.get("codigo_postal"), req_id, "ST002", meta.get("source_blob"),
            1 if warnings else 0, "; ".join(warnings) if warnings else None,
        )
        for b in beneficiaries:
            cur.execute(
                """INSERT INTO fact_intern_beneficiaries
                   (beneficiary_id, intern_id, nombre, paterno, materno, parentesco, porcentaje, source_blob)
                   VALUES (?,?,?,?,?,?,?,?)""",
                "BEN-" + str(uuid.uuid4())[:8], pra_id, b["nombre"], b["paterno"], b["materno"],
                b["parentesco"], b["porcentaje"], meta.get("source_blob"),
            )
        conn.commit()
        # confirmation / welcome to the candidate
        send_email(fields.get("email_personal") or "candidate",
                   "¡Te damos la bienvenida a Cemex! Documentos – Summer Internship Program",
                   f"Hola {fields.get('nombre')}, recibimos y validamos tu información correctamente. "
                   f"Tu registro es {pra_id}" + (f", vinculado a la posición {req_id}." if req_id else ".") +
                   " En breve te enviaremos tu convenio y documentos para firma.")
        result = {"type": "candidate", "status": "created", "intern_id": pra_id,
                  "requisition_id": req_id, "beneficiaries": len(beneficiaries), "warnings": warnings}
        print(f"CANDIDATE → {pra_id} linked={req_id} beneficiarios={len(beneficiaries)} warnings={len(warnings)}")
        return result
    finally:
        cur.close(); conn.close()


def process_onboarding_file(local_path, filename, meta=None):
    kind = classify_document(local_path, filename)
    if kind == "requisicion":
        return process_requisicion(local_path, meta)
    if kind == "alta_candidate":
        return process_candidate(local_path, meta)
    return {"type": kind, "status": "skipped_not_onboarding"}
