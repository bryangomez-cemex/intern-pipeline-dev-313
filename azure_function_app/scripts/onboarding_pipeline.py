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
import json
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

import email_service

# Fixed RH recipients for HR notifications. Coparmex packages are sent to RH only;
# RH reviews quickly and forwards externally. Practicantes usually have CEMEX
# emails; new hires may still use personal emails until their CEMEX account exists.
RH_RECIPIENT_EMAILS = os.getenv("RH_RECIPIENT_EMAILS", "")


def _parse_emails(value):
    """Email list env var → cleaned emails. Accepts comma, semicolon, or newline
    separators (Outlook commonly uses ';'); trims whitespace and drops empties."""
    normalized = (value or "").replace(";", ",").replace("\n", ",")
    return [e.strip() for e in normalized.split(",") if e.strip()]


POWERBI_LINK_LABEL = "PowerBI - Practicantes"
POWERBI_LINK_TOKEN = "{{POWERBI_LINK}}"  # replaced with a hyperlink by _text_to_html


def _text_to_html(text):
    """Minimal plain-text → HTML so existing newline-formatted bodies render.
    POWERBI_LINK_TOKEN becomes a clickable 'PowerBI - Practicantes' hyperlink."""
    import html as _html
    body = _html.escape(str(text or "")).replace("\n", "<br>")
    if POWERBI_DASHBOARD_URL:
        link = f'<a href="{POWERBI_DASHBOARD_URL.replace("&", "&amp;")}">{POWERBI_LINK_LABEL}</a>'
    else:
        link = POWERBI_LINK_LABEL
    body = body.replace(POWERBI_LINK_TOKEN, link)
    return "<html><body style=\"font-family:Arial,sans-serif\">" + body + "</body></html>"


def resolve_person_email(personal_email, cemex_email, person_type="new_hire"):
    """Pick the right recipient address by person/process type.
    - practicante/intern: prefer the CEMEX (institutional) email.
    - new hire / alta / contratacion: prefer the personal email.
    Falls back to the other valid field when the preferred one is missing.
    """
    prefer_cemex = str(person_type or "").lower() in ("practicante", "intern", "current_intern")
    primary = cemex_email if prefer_cemex else personal_email
    secondary = personal_email if prefer_cemex else cemex_email
    return (primary or "").strip() or (secondary or "").strip() or None

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


def extract_requisition_id(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, dict):
            value = " ".join(str(v) for v in value.values() if v)
        match = REQ_IN_TEXT.search(str(value))
        if match:
            return match.group(0).upper()
    return None


def resolve_requisition_id(cursor, meta=None, *values):
    meta = meta or {}
    req_id = extract_requisition_id(
        meta.get("requisition_id"),
        meta.get("email_subject"),
        meta.get("source_blob"),
        meta.get("source_container"),
        meta.get("body_fields"),
        *values,
    )

    if not req_id:
        return None, None

    cursor.execute(
        "SELECT requisition_id, carrera_requerida FROM dim_requisitions WHERE requisition_id=?",
        req_id,
    )
    row = cursor.fetchone()
    if not row:
        return None, f"REQ detectado ({req_id}) pero no existe en dim_requisitions."

    return req_id, {"requisition_id": row[0], "carrera_requerida": row[1]}


def _next_sequential_id(cursor, table, column, prefix):
    resource = f"intern-pipeline:{table}:{column}:{prefix}:{datetime.now(UTC).year}"
    cursor.execute(
        """
        DECLARE @lock_result INT;
        EXEC @lock_result = sys.sp_getapplock
            @Resource = ?,
            @LockMode = 'Exclusive',
            @LockOwner = 'Transaction',
            @LockTimeout = 30000,
            @DbPrincipal = 'public';
        SELECT @lock_result;
        """,
        resource,
    )
    lock_result = cursor.fetchone()[0]
    if lock_result < 0:
        raise RuntimeError(f"Could not acquire SQL sequence lock for {prefix}: {lock_result}")

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
        if "id vacante" in blob and ("estatus general" in blob or "promedio dias abierto" in blob):
            return "open_positions"
        if "datos del practicante" in blob or "administracion de practicantes" in blob or "curp" in blob and "beneficiarios" in blob:
            return "alta_candidate"
        if "numero de puesto" in blob or "personal email" in blob or "cemex id" in blob or "cemex-id" in blob:
            return "hr_new_hires"
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
# email — delegates to the central SMTP service
# ============================================================

def send_email(intended_to, subject, body, attachments=None, to_name=None, cc=None, metadata=None):
    """Thin wrapper over email_service. Keeps the existing call sites:
    plain-text bodies are converted to HTML; attachments are passed through
    to the central sender."""
    if not intended_to:
        return {"status": "failed", "provider": email_service.PROVIDER, "error": "missing recipient"}
    result = email_service.send_email(
        to_email=intended_to,
        subject=subject,
        html_body=_text_to_html(body),
        to_name=to_name,
        cc=cc,
        attachments=attachments,
        metadata=metadata,
    )
    note = f" + {len(attachments)} attachment(s)" if attachments else ""
    print(f"[EMAIL] to={intended_to} subj={subject!r} -> {result.get('status')}{note}")
    return result


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
        else:
            send_email(meta.get("sender_email") or "solicitante",
                       f"Requisición recibida – ID de posición {req_id}",
                       f"Tu requisición para '{fields.get('puesto') or ''}' fue procesada correctamente.\n\n"
                       f"El ID de posición es: {req_id}\n\n"
                       "Inclúyelo en la lista de new hires (columna 'NUMERO DE PUESTO') o en el cuerpo del "
                       "correo para vincular al practicante con esta posición. El sistema usa metadatos del "
                       "correo y contenido de archivos, no depende de un subject fijo.")
        result = {"type": "requisicion", "status": "needs_review" if fields.get("needs_review") else "created",
                  "requisition_id": req_id, "puesto": fields.get("puesto")}
        print(f"REQUISICIÓN → {req_id} ({result['status']}) puesto={fields.get('puesto')}")
        return result
    finally:
        cur.close(); conn.close()


def apply_email_body_fields(cur, intern_id, meta):
    """Fill candidate fields the intern supplied in the Welcome 1 email body
    (teléfono, apodo, LinkedIn, fecha de graduación). COALESCE so the alta wins."""
    raw = (meta or {}).get("body_fields")
    if not raw or not intern_id:
        return {}
    try:
        body = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return {}
    cols = {
        "telefono": "telefono",
        "apodo": "apodo",
        "linkedin": "linkedin",
        "fecha_graduacion": "fecha_graduacion",
        "contacto_emergencia": "contacto_emergencia",
    }
    sets, vals = [], []
    for key, col in cols.items():
        if body.get(key):
            sets.append(f"[{col}] = COALESCE([{col}], ?)")
            vals.append(str(body[key])[:200])
    if sets:
        cur.execute(f"UPDATE dim_interns SET {', '.join(sets)} WHERE intern_id = ?", *vals, intern_id)
    return body


def process_candidate(local_path, meta=None):
    meta = meta or {}
    fields, beneficiaries = parse_alta_excel(local_path)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        req_id, requisicion = resolve_requisition_id(cur, meta, fields)

        errors, warnings = validate_candidate(fields, requisicion)
        if not req_id:
            warnings.append("sin Position ID (REQ) — practicante no vinculado a una requisición.")

        if errors:
            _return_to_sender(meta.get("sender_email"),
                              f"alta de {fields.get('nombre_completo') or 'practicante'}", errors)
            conn.commit()
            print(f"CANDIDATE returned to sender: {len(errors)} error(s)")
            return {"type": "candidate", "status": "returned", "errors": errors}

        # Match the candidate the HR list already created (by email / sender / position)
        # to ENRICH it with the alta; only insert a new row if none exists.
        existing = None
        for lookup_email in (fields.get("email_personal"), meta.get("sender_email")):
            if lookup_email and not existing:
                cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE LOWER(email_personal)=LOWER(?)", lookup_email)
                rr = cur.fetchone(); existing = rr[0] if rr else None
        if not existing and req_id:
            cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE requisition_id=? AND (curp IS NULL OR curp='')", req_id)
            rr = cur.fetchone(); existing = rr[0] if rr else None

        alta_cols = {
            "nombre": fields.get("nombre"), "paterno": fields.get("paterno"), "materno": fields.get("materno"),
            "nombre_completo": fields.get("nombre_completo"), "sexo": fields.get("sexo"),
            "curp": (fields.get("curp") or "").upper() or None, "carrera": fields.get("carrera"),
            "semestre": fields.get("semestre_requerido") or fields.get("grado"),
            "email_personal": fields.get("email_personal"), "telefono": fields.get("telefono"),
            "estado_civil": fields.get("estado_civil"), "nacionalidad": fields.get("nacionalidad"),
            "matricula": fields.get("matricula"), "grado": fields.get("grado"),
            "fecha_nacimiento": fields.get("fecha_nacimiento"), "calle": fields.get("calle"),
            "numero_exterior": fields.get("numero_exterior"), "colonia": fields.get("colonia"),
            "poblacion": fields.get("poblacion"), "estado_direccion": fields.get("estado_direccion"),
            "codigo_postal": fields.get("codigo_postal"),
        }
        if existing:
            pra_id = existing
            sets, vals = [], []
            for col, val in alta_cols.items():
                if val is not None:
                    sets.append(f"[{col}] = COALESCE([{col}], ?)"); vals.append(val)
            if req_id:
                sets.append("[requisition_id] = COALESCE([requisition_id], ?)"); vals.append(req_id)
            sets.append("[candidate_source_blob] = ?"); vals.append(meta.get("source_blob"))
            cur.execute(f"UPDATE dim_interns SET {', '.join(sets)} WHERE intern_id=?", *vals, pra_id)
            status = "enriched"
        else:
            pra_id = _next_sequential_id(cur, "dim_interns", "intern_id", "PRA")
            cur.execute(
                """INSERT INTO dim_interns
                   (intern_id, nombre, paterno, materno, nombre_completo, sexo, curp, carrera, semestre,
                    email_personal, telefono, estado_civil, nacionalidad, matricula, grado,
                    fecha_nacimiento, calle, numero_exterior, colonia, poblacion, estado_direccion, codigo_postal,
                    requisition_id, status_id, candidate_source_blob, candidate_needs_review, candidate_validation_notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                pra_id, *[alta_cols[k] for k in ("nombre","paterno","materno","nombre_completo","sexo","curp","carrera","semestre",
                          "email_personal","telefono","estado_civil","nacionalidad","matricula","grado","fecha_nacimiento",
                          "calle","numero_exterior","colonia","poblacion","estado_direccion","codigo_postal")],
                req_id, "ST002", meta.get("source_blob"),
                1 if warnings else 0, "; ".join(warnings) if warnings else None,
            )
            status = "created"

        cur.execute("DELETE FROM fact_intern_beneficiaries WHERE intern_id=?", pra_id)
        for b in beneficiaries:
            cur.execute(
                """INSERT INTO fact_intern_beneficiaries
                   (beneficiary_id, intern_id, nombre, paterno, materno, parentesco, porcentaje, source_blob)
                   VALUES (?,?,?,?,?,?,?,?)""",
                "BEN-" + str(uuid.uuid4())[:8], pra_id, b["nombre"], b["paterno"], b["materno"],
                b["parentesco"], b["porcentaje"], meta.get("source_blob"),
            )
        apply_email_body_fields(cur, pra_id, meta)
        # record the alta as a received pack-1 document (for the completeness check)
        cur.execute(
            """IF NOT EXISTS (SELECT 1 FROM fact_intern_documents WHERE intern_id=? AND stage='candidate_docs' AND document_type='alta')
               INSERT INTO fact_intern_documents (document_id, intern_id, stage, document_type, file_name, blob_path, name_match, status)
               VALUES (?,?, 'candidate_docs','alta',?,?, 1,'received')""",
            pra_id, "DOC-" + str(uuid.uuid4())[:8], pra_id,
            os.path.basename(meta.get("source_blob") or "alta.xlsx"), meta.get("source_blob"))
        conn.commit()
        try:
            import document_pipeline
            document_pipeline.check_candidate_documents_complete(
                pra_id, sender_email=meta.get("sender_email"), notify_incomplete=False)
        except Exception as ce:
            print("pack1 check note:", ce)
        result = {"type": "candidate", "status": status, "intern_id": pra_id,
                  "requisition_id": req_id, "beneficiaries": len(beneficiaries), "warnings": warnings}
        print(f"CANDIDATE → {pra_id} ({status}) linked={req_id} beneficiarios={len(beneficiaries)}")
        return result
    finally:
        cur.close(); conn.close()


def process_onboarding_file(local_path, filename, meta=None):
    kind = classify_document(local_path, filename)
    if kind == "requisicion":
        return process_requisicion(local_path, meta)
    if kind == "alta_candidate":
        return process_candidate(local_path, meta)
    if kind == "hr_new_hires":
        return process_hr_new_hires(local_path, meta)
    if kind == "open_positions":
        return process_open_positions(local_path, meta)
    return {"type": kind, "status": "skipped_not_onboarding"}


# ============================================================
# HR new-hires list → match to candidate + complete the data
# ============================================================

HR_COLUMN_MAP = {
    "nombre": "nombre_completo", "nombre completo": "nombre_completo",
    "personal email": "email_personal", "correo personal": "email_personal", "email personal": "email_personal",
    "numero de puesto": "requisition_id", "id requisicion": "requisition_id", "posicion": "requisition_id",
    "cemex id": "cemex_id", "cemexid": "cemex_id",
    "correo institucional": "correo_institucional", "correo institucional cemex": "correo_institucional",
    "email cemex": "correo_institucional", "correo cemex": "correo_institucional",
    "ubicacion udn": "ubicacion_udn", "udn": "ubicacion_udn",
    "compania": "compania", "cia hc": "compania", "razon social": "compania", "razon social hc": "compania",
    "ubicacion estado": "ubicacion_estado", "ubicacion estado de practicante": "ubicacion_estado",
    "ubicacion edo": "ubicacion_estado", "edo": "ubicacion_estado",
    "oi": "oi", "oi hc": "oi", "orden interna": "oi",
    "cc": "cc", "cc hc": "cc", "centro de costo": "cc",
    "carrera": "carrera", "universidad": "universidad", "semestre": "semestre",
    "fecha de graduacion": "fecha_graduacion", "graduacion": "fecha_graduacion",
}

HR_PERSIST_FIELDS = ["cemex_id", "correo_institucional", "ubicacion_udn", "compania",
                     "ubicacion_estado", "oi", "cc", "fecha_graduacion"]


def _map_hr_row(row, headers):
    out = {}
    for header, value in zip(headers, row):
        norm = re.sub(r"\s+", " ", _norm(header).replace("-", " ").replace("/", " ")).strip()
        field = HR_COLUMN_MAP.get(norm)
        if field and _clean(value) is not None:
            out[field] = _clean(value)
    return out


def _match_candidate(cur, hr_row):
    """Match an HR row to an existing candidate: by Position ID if present,
    otherwise by personal email, otherwise by full name."""
    req = hr_row.get("requisition_id")
    email = hr_row.get("email_personal")
    name = hr_row.get("nombre_completo")
    if req:
        cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE requisition_id = ?", req)
        r = cur.fetchone()
        if r:
            return r[0], f"matched by Position ID {req}"
    if email:
        cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE LOWER(email_personal) = LOWER(?)", email)
        r = cur.fetchone()
        if r:
            return r[0], f"matched by email {email}"
    if name:
        cur.execute("SELECT TOP 1 intern_id FROM dim_interns WHERE LOWER(nombre_completo) = LOWER(?)", name)
        r = cur.fetchone()
        if r:
            return r[0], f"matched by name {name}"
    return None, "no candidate matched"


def _name_key(name):
    """Order-independent signature of a person name so 'APELLIDOS, NOMBRE' and
    'NOMBRE APELLIDOS' match. Lowercased, de-accented, punctuation removed, sorted."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    tokens = re.sub(r"[^a-z0-9 ]", " ", text.lower()).split()
    return " ".join(sorted(tokens))


def load_manager_assignments(local_path):
    """Load the W1 layout (jefe directo → OI/CC/compañía/UDN/estado/VP/asesor) into
    dim_manager_assignments, keyed by a normalized jefe-name signature."""
    df = pd.read_excel(local_path)
    col = {c: c for c in df.columns}
    conn = azure_clients.get_sql_connection()
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""IF OBJECT_ID('dbo.dim_manager_assignments','U') IS NULL
        CREATE TABLE dbo.dim_manager_assignments (
          jefe_key NVARCHAR(300) NOT NULL PRIMARY KEY, jefe_directo NVARCHAR(200) NULL,
          vp NVARCHAR(200) NULL, asesor_rh NVARCHAR(200) NULL, ubicacion_udn NVARCHAR(200) NULL,
          estado NVARCHAR(100) NULL, compania NVARCHAR(200) NULL, oi NVARCHAR(50) NULL,
          cc NVARCHAR(50) NULL, updated_at DATETIME2 DEFAULT SYSUTCDATETIME())""")
    loaded = 0
    for _, r in df.iterrows():
        jefe = _clean(r.get("JefeInmediato"))
        if not jefe:
            continue
        key = _name_key(jefe)
        vals = (key, jefe, _clean(r.get("VP HC")), _clean(r.get("ASESOR RRHH HC")),
                _clean(r.get("UBICACIÓN HC")), _clean(r.get("ESTADO UBICACIÓN HC")),
                _clean(r.get("RAZON SOCIAL HC")), _clean(r.get("OI HC")), _clean(r.get("CC HC")))
        cur.execute("""MERGE dbo.dim_manager_assignments AS t
            USING (SELECT ? AS jefe_key) AS s ON t.jefe_key = s.jefe_key
            WHEN MATCHED THEN UPDATE SET jefe_directo=?, vp=?, asesor_rh=?, ubicacion_udn=?, estado=?, compania=?, oi=?, cc=?, updated_at=SYSUTCDATETIME()
            WHEN NOT MATCHED THEN INSERT (jefe_key, jefe_directo, vp, asesor_rh, ubicacion_udn, estado, compania, oi, cc)
            VALUES (?,?,?,?,?,?,?,?,?);""",
            key, vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8],
            key, vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], vals[8])
        loaded += 1
    conn.close()
    return loaded


def get_manager_assignment(cursor, manager_name):
    key = _name_key(manager_name)
    if not key:
        return {}
    cursor.execute(
        "SELECT oi, cc, compania, ubicacion_udn, estado FROM dim_manager_assignments WHERE jefe_key = ?",
        key,
    )
    r = cursor.fetchone()
    if not r:
        return {}
    return {"oi": r[0], "cc": r[1], "compania": r[2], "ubicacion_udn": r[3], "estado_w1": r[4]}


def _get_alta_template():
    """Download the blank Coparmex alta format (attached to Welcome 1)."""
    try:
        import tempfile
        client = azure_clients.get_blob_service_client().get_blob_client(
            container="archive", blob="templates/alta_coparmex.xlsx")
        tmp = tempfile.NamedTemporaryFile(suffix="_alta_coparmex.xlsx", delete=False)
        tmp.write(client.download_blob().readall()); tmp.close()
        return tmp.name, True
    except Exception as e:
        print(f"alta template not available: {e}")
        return None, False


def _create_candidate_from_hr(cur, hr_row):
    pra_id = _next_sequential_id(cur, "dim_interns", "intern_id", "PRA")
    full = hr_row.get("nombre_completo")
    cur.execute(
        """INSERT INTO dim_interns (intern_id, nombre, nombre_completo, email_personal,
           requisition_id, status_id, hr_list_matched)
           VALUES (?,?,?,?,?, 'ST002', 1)""",
        pra_id, (full.split()[0] if full else None), full, hr_row.get("email_personal"),
        hr_row.get("requisition_id"))
    return pra_id


def send_pack1(cur, intern_id):
    """Paquete 1: ask the new hire for data + documents, attach the alta format."""
    cur.execute("SELECT nombre, nombre_completo, email_personal, correo_institucional FROM dim_interns WHERE intern_id=?", intern_id)
    r = cur.fetchone()
    if not r:
        return
    name = r[0] or (r[1].split()[0] if r[1] else "practicante")
    to_email = resolve_person_email(r[2], r[3], person_type="new_hire")  # new hires prefer personal
    tmpl, is_temp = _get_alta_template()
    send_email(to_email or "candidate",
               "¡Te damos la bienvenida a Cemex! Paquete 1 – Summer Internship Program",
               f"¡Hola {name}! Estamos iniciando tu proceso de ingreso.\n\n"
               "Por favor RESPONDE a este correo con tus datos:\n"
               "Nombre completo:\n¿Cómo te gusta que te digan?:\nFecha de nacimiento:\n"
               "Fecha estimada de graduación:\nTeléfono celular:\nLinkedIn:\n\n"
               "Contacto de emergencia (nombre, parentesco y teléfono):\n\n"
               "Y ADJUNTA estos documentos: Acta de nacimiento, Constancia de estudios, "
               "Identificación oficial, CURP, Comprobante de domicilio y el formato de alta adjunto "
               "(lleno).\n\nPuedes responder con el subject que ya tenga tu correo; el sistema usa el "
               "contenido y los metadatos del mensaje para clasificarlo.",
               attachments=[tmpl] if tmpl else None)
    cur.execute("UPDATE dim_interns SET documents_status = COALESCE(documents_status, 'pack1_requested') WHERE intern_id=?", intern_id)
    if is_temp and tmpl:
        try:
            os.unlink(tmpl)
        except OSError:
            pass


def process_hr_new_hires(local_path, meta=None):
    df = pd.read_excel(local_path, header=0)
    headers = list(df.columns)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    processed = []
    try:
        for _, raw in df.iterrows():
            hr_row = _map_hr_row(raw.tolist(), headers)
            if not hr_row.get("requisition_id"):
                hr_row["requisition_id"] = extract_requisition_id(meta, hr_row, headers)
            if not any(hr_row.get(k) for k in ("requisition_id", "email_personal", "nombre_completo")):
                continue
            intern_id, how = _match_candidate(cur, hr_row)
            if not intern_id:
                intern_id = _create_candidate_from_hr(cur, hr_row)
                how = "created from HR list"
            sets, vals = [], []
            for f in HR_PERSIST_FIELDS:
                if hr_row.get(f) is not None:
                    sets.append(f"[{f}] = ?"); vals.append(hr_row[f])
            if hr_row.get("requisition_id"):
                sets.append("[requisition_id] = COALESCE([requisition_id], ?)"); vals.append(hr_row["requisition_id"])
            sets.append("[hr_list_matched] = 1")
            cur.execute(f"UPDATE dim_interns SET {', '.join(sets)} WHERE intern_id = ?", *vals, intern_id)
            send_pack1(cur, intern_id)            # step 5: pack 1 to the new hire
            conn.commit()
            processed.append({"intern_id": intern_id, "how": how})
            print(f"HR new-hire {how} → {intern_id}; Paquete 1 sent")
        result = {"type": "hr_new_hires", "status": "processed",
                  "count": len(processed), "interns": processed}
        print(f"HR NEW-HIRES → {len(processed)} new hire(s), Paquete 1 sent")
        return result
    finally:
        cur.close(); conn.close()


# ============================================================
# Open positions list (NOT a requisition) → dim_open_positions snapshot
# ============================================================

OPEN_POSITIONS_COLUMNS = {
    "#": "numero", "no": "numero", "num": "numero",
    "vacante": "vacante",
    "id vacante": "id_vacante", "idvacante": "id_vacante",
    "ubicacion": "ubicacion",
    "promedio dias abierto": "promedio_dias_abierto", "dias abierto": "promedio_dias_abierto",
    "responsable": "responsable",
    "airh": "airh",
    "jefe del puesto": "jefe_puesto", "jefe puesto": "jefe_puesto",
    "estatus general": "estatus_general", "estatus": "estatus_general",
}


def _to_int(value):
    try:
        return int(float(value)) if value not in (None, "") else None
    except Exception:
        return None


def process_open_positions(local_path, meta=None):
    """Ingest a 'lista de posiciones actualmente abiertas' (open vacancies snapshot).
    Each upload replaces the current snapshot (is_current). Not a requisition."""
    meta = meta or {}
    df = pd.read_excel(local_path, header=0)
    headers = list(df.columns)
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        cur.execute("""IF OBJECT_ID('dbo.dim_open_positions','U') IS NULL
            CREATE TABLE dbo.dim_open_positions (
              position_row_id NVARCHAR(50) NOT NULL PRIMARY KEY, numero INT NULL,
              vacante NVARCHAR(300) NULL, id_vacante NVARCHAR(50) NULL, ubicacion NVARCHAR(200) NULL,
              promedio_dias_abierto INT NULL, responsable NVARCHAR(200) NULL, airh NVARCHAR(200) NULL,
              jefe_puesto NVARCHAR(200) NULL, estatus_general NVARCHAR(200) NULL,
              is_current BIT NOT NULL DEFAULT 1, source_blob NVARCHAR(400) NULL,
              updated_at DATETIME2 DEFAULT SYSUTCDATETIME())""")
        # snapshot replace: previous list is no longer current
        cur.execute("UPDATE dbo.dim_open_positions SET is_current = 0")
        loaded = 0
        for _, raw in df.iterrows():
            row = {}
            for header, value in zip(headers, raw.tolist()):
                key = re.sub(r"\s+", " ", _norm(str(header)).replace("-", " ").replace("/", " ")).strip()
                field = OPEN_POSITIONS_COLUMNS.get(key)
                if field and _clean(value) is not None:
                    row[field] = _clean(value)
            if not row.get("vacante"):
                continue
            idv = row.get("id_vacante")
            if idv and str(idv).strip().upper() in ("NA", "N/A", "NONE", "-", ""):
                idv = None
            cur.execute(
                """INSERT INTO dbo.dim_open_positions
                   (position_row_id, numero, vacante, id_vacante, ubicacion, promedio_dias_abierto,
                    responsable, airh, jefe_puesto, estatus_general, is_current, source_blob)
                   VALUES (?,?,?,?,?,?,?,?,?,?,1,?)""",
                "POS-" + str(uuid.uuid4())[:8], _to_int(row.get("numero")), row.get("vacante"), idv,
                row.get("ubicacion"), _to_int(row.get("promedio_dias_abierto")), row.get("responsable"),
                row.get("airh"), row.get("jefe_puesto"), row.get("estatus_general"), meta.get("source_blob"))
            loaded += 1
        conn.commit()
        print(f"OPEN POSITIONS → {loaded} posicion(es) abierta(s) cargadas")
        return {"type": "open_positions", "status": "loaded", "count": loaded}
    finally:
        cur.close(); conn.close()


# ============================================================
# Coparmex package + final notifications (lifecycle stage F)
# ============================================================

POWERBI_DASHBOARD_URL = os.getenv("POWERBI_DASHBOARD_URL", "https://app.powerbi.com/<intern-dashboard>")
FIXED_SUELDO = "$8800"

# OI / CC tables keyed by jefe directo — to be provided. Empty for now → those
# fields report as missing, which (per the rules) blocks the Coparmex send.
OI_BY_MANAGER = {}
CC_BY_MANAGER = {}

# Coparmex needs these, and they come from the HR new-hires list / OI-CC tables.
# If any is missing, do NOT send Coparmex — notify RH to complete the data instead.
COPARMEX_REQUIRED_FROM_HR = [
    "cemex_id", "correo_institucional", "ubicacion_udn", "compania",
    "ubicacion_estado", "oi", "cc",
]


def _resolve_recipients(cursor):
    """RH notification recipients. Coparmex workflow is sent to RH only; RH
    forwards externally after a quick check. Fall back to dim_email_recipients if
    the RH env list is not configured."""
    out = {"HR": _parse_emails(RH_RECIPIENT_EMAILS), "Coparmex": []}
    if not out["HR"]:
        try:
            cursor.execute(
                "SELECT recipient_group, email FROM dim_email_recipients "
                "WHERE active_flag = 1 AND recipient_group = 'HR'"
            )
            for group, email in cursor.fetchall():
                if email and group == "HR":
                    out["HR"] = out["HR"] + [email]
        except Exception as e:
            print("recipient resolve note:", e)
    # Collapse to a ';'-joined string (or None) for the existing call sites.
    return {g: (";".join(v) if v else None) for g, v in out.items()}


def build_coparmex_package(requisicion, candidate, hr_data=None):
    hr_data = hr_data or {}
    manager = (requisicion or {}).get("manager_name")
    fields = {
        "Nombre completo": candidate.get("nombre_completo"),
        "Fecha de nacimiento": candidate.get("fecha_nacimiento"),
        "Correo personal": candidate.get("email_personal"),
        "Universidad": candidate.get("universidad") or candidate.get("nombre_escuela"),
        "Carrera": candidate.get("carrera"),
        "Semestre": candidate.get("semestre"),
        "Fecha de graduación": candidate.get("fecha_graduacion"),
        "CEMEX-ID": hr_data.get("cemex_id"),
        "Correo institucional CEMEX": hr_data.get("correo_institucional"),
        "Vicepresidencia": (requisicion or {}).get("vp"),
        "Nombre del proyecto": (requisicion or {}).get("descripcion_proyecto"),
        "Jefe directo": manager,
        "AIRH": (requisicion or {}).get("asesor_rh"),
        "Ubicación UDN": hr_data.get("ubicacion_udn"),
        "Compañia": hr_data.get("compania"),
        "OI": hr_data.get("oi") or OI_BY_MANAGER.get(manager),
        "CC": hr_data.get("cc") or CC_BY_MANAGER.get(manager),
        "Sueldo": candidate.get("salario_mensual") or FIXED_SUELDO,
        "Fecha de ingreso": (requisicion or {}).get("fecha_inicio_solicitada"),
        "Fecha fin": (requisicion or {}).get("fecha_termino_solicitada"),
        "Ubicacion Estado de practicante": hr_data.get("ubicacion_estado"),
    }
    key_map = {
        "cemex_id": "CEMEX-ID", "correo_institucional": "Correo institucional CEMEX",
        "ubicacion_udn": "Ubicación UDN", "compania": "Compañia",
        "ubicacion_estado": "Ubicacion Estado de practicante", "oi": "OI", "cc": "CC",
    }
    missing = [key_map[k] for k in COPARMEX_REQUIRED_FROM_HR if not fields.get(key_map[k])]
    return fields, missing


def _format_coparmex_email(fields):
    lines = ["Se adjunta la información relacionada.", "", "FAVOR DE GESTIONAR CONVENIO."]
    for label, value in fields.items():
        lines.append(f"{label}: {value if value not in (None, '') else ''}")
    return "\n".join(lines)


def finalize_onboarding(intern_id, hr_data=None):
    """Stage F: after the candidate and HR data are in, prepare the Coparmex
    package for RH to review/forward. If the system cannot resolve required fields,
    notify RH with the specific missing data instead."""
    conn = azure_clients.get_sql_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT intern_id, nombre, nombre_completo, email_personal, carrera, semestre, "
            "universidad, fecha_nacimiento, fecha_graduacion, requisition_id, "
            "cemex_id, correo_institucional, ubicacion_udn, compania, ubicacion_estado, oi, cc, "
            "salario_mensual "
            "FROM dim_interns WHERE intern_id = ?",
            intern_id,
        )
        row = cur.fetchone()
        if not row:
            return {"status": "not_found", "intern_id": intern_id}
        cols = [d[0] for d in cur.description]
        candidate = dict(zip(cols, row))

        # HR-sourced fields come from the candidate row (persisted by the HR-list
        # ingestion); an explicit hr_data arg overrides when provided.
        persisted_hr = {f: candidate.get(f) for f in
                        ("cemex_id", "correo_institucional", "ubicacion_udn", "compania",
                         "ubicacion_estado", "oi", "cc")}
        if hr_data:
            persisted_hr.update({k: v for k, v in hr_data.items() if v})
        hr_data = persisted_hr

        requisicion = None
        req_id = candidate.get("requisition_id")
        if req_id:
            cur.execute(
                "SELECT vp, descripcion_proyecto, manager_name, asesor_rh, "
                "fecha_inicio_solicitada, fecha_termino_solicitada FROM dim_requisitions WHERE requisition_id = ?",
                req_id,
            )
            r = cur.fetchone()
            if r:
                requisicion = dict(zip([d[0] for d in cur.description], r))

        # OI/CC/compañía/UDN come from the W1 layout, keyed by the jefe directo on
        # the requisición — fill whatever the HR list did not already provide.
        if requisicion and requisicion.get("manager_name"):
            w1 = get_manager_assignment(cur, requisicion["manager_name"])
            for k in ("oi", "cc", "compania", "ubicacion_udn"):
                if not hr_data.get(k) and w1.get(k):
                    hr_data[k] = w1[k]
            if not hr_data.get("ubicacion_estado") and w1.get("estado_w1"):
                hr_data["ubicacion_estado"] = w1["estado_w1"]

        fields, missing = build_coparmex_package(requisicion, candidate, hr_data)
        recipients = _resolve_recipients(cur)
        name = candidate.get("nombre") or candidate.get("nombre_completo") or "practicante"

        # Always thank the practicante.
        send_email(candidate.get("email_personal") or "candidate",
                   "Gracias – Summer Internship Program",
                   f"Hola {name}, muchas gracias. Recibimos y procesamos tu información. "
                   "Nos pondremos en contacto contigo muy pronto con los siguientes pasos.")

        if missing:
            # Data incomplete after matching → ask RH only in this rare unresolved case.
            send_email(recipients["HR"] or "hr",
                       f"Practicante procesado – faltan datos para Coparmex ({candidate.get('nombre_completo')})",
                       f"El expediente de {candidate.get('nombre_completo')} se procesó correctamente, pero la "
                       f"base de datos no pudo encontrar/hacer match de: {', '.join(missing)}.\n\n"
                       f"Por ello NO se preparó el correo de gestión Coparmex para RH. Por favor completen estos "
                       f"datos en la base/archivo fuente (incluyendo el número de puesto {req_id or '(sin posición)'} "
                       f"cuando aplique) y reenvíenlo al sistema. Esto debería ser un caso raro porque el matching "
                       f"intenta resolverlos automáticamente.\n\n"
                       f"Datos disponibles en {POWERBI_LINK_TOKEN}")
            result = {"status": "rh_notified_missing", "intern_id": intern_id,
                      "requisition_id": req_id, "missing": missing, "coparmex_ready_for_rh": False}
        else:
            # Complete → send the Coparmex-ready email to RH only. RH reviews and forwards.
            send_email(recipients["HR"] or "hr",
                       f"FAVOR DE GESTIONAR CONVENIO (RH reenviar a Coparmex) - {candidate.get('nombre_completo')}",
                       _format_coparmex_email(fields) +
                       "\n\nRH: favor de revisar esta informacion y reenviarla a Coparmex." +
                       "\n\n(Se adjunta NA FORMATO PARA ALTA DE PRACTICANTE COPARMEX.xlsx)")
            send_email(recipients["HR"] or "hr",
                       "Practicante dado de alta exitosamente",
                       f"El practicante {candidate.get('nombre_completo')} (posición {req_id}) fue dado de alta "
                       f"exitosamente y la gestión Coparmex quedó preparada para revisión/reenvío por RH.\n\n"
                       f"Para acceder a los datos, visita {POWERBI_LINK_TOKEN}")
            result = {"status": "coparmex_ready_for_rh", "intern_id": intern_id,
                      "requisition_id": req_id, "coparmex_ready_for_rh": True}

        conn.commit()
        print(f"FINALIZE {intern_id}: {result['status']}" + (f" missing={missing}" if missing else ""))
        return result
    finally:
        cur.close(); conn.close()
