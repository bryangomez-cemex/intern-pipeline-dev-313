"""
Rule-based extractor for the Coparmex "ALTA PRACTICANTE" Excel format.

The form is a key-value-in-cells layout grouped into sections (Datos del
practicante / escuela / empresa / Beneficiarios). We read it as a grid, scope
field extraction to the practicante section, and read the beneficiarios table
positionally. Returns a candidate dict (+ a beneficiarios list).
"""

import re
from datetime import datetime

import pandas as pd


SECTION_MARKERS = {
    "datos del practicante": "practicante",
    "datos de la escuela": "escuela",
    "datos de la empresa": "empresa",
    "beneficiarios": "beneficiarios",
}

PRACTICANTE_LABELS = {
    "nombres": "nombre", "apellido paterno": "paterno", "apellido materno": "materno",
    "sexo": "sexo", "estado civil": "estado_civil", "nacionalidad": "nacionalidad",
    "matricula": "matricula", "carrera": "carrera", "grado": "grado",
    "calle": "calle", "numero exterior": "numero_exterior", "colonia": "colonia",
    "poblacion": "poblacion", "estado": "estado", "codigo postal": "codigo_postal",
    "telefono": "telefono", "mail": "email_personal", "correo": "email_personal",
    "fecha de nacimiento": "fecha_nacimiento", "curp": "curp",
}

CURP_RE = re.compile(r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$")


def _norm(value):
    return re.sub(r"[*:]", "", str(value)).strip().lower()


def _is_percentage(value):
    try:
        float(str(value).replace("%", "").strip())
        return True
    except ValueError:
        return False


def _parse_dob(value):
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def extract_alta(path):
    df = pd.ExcelFile(path).parse(0, header=None)
    fields = {}
    beneficiarios = []
    section = None
    ben_header_seen = False

    for _, row in df.iterrows():
        cells = [str(v).strip() for v in row.tolist() if str(v).strip() and str(v) != "nan"]
        if not cells:
            continue

        if _norm(cells[0]) in SECTION_MARKERS:
            section = SECTION_MARKERS[_norm(cells[0])]
            ben_header_seen = False
            continue

        if section == "practicante":
            for i in range(len(cells) - 1):
                label = _norm(cells[i])
                if label in PRACTICANTE_LABELS and PRACTICANTE_LABELS[label] not in fields:
                    fields[PRACTICANTE_LABELS[label]] = cells[i + 1].strip()

        elif section == "beneficiarios":
            if not ben_header_seen:
                if any(("nombres" in _norm(c)) or ("parentesco" in _norm(c)) for c in cells):
                    ben_header_seen = True
                continue
            # A real beneficiario row ends in a numeric percentage. Rows without one
            # are the document checklist that sits below the table — skip them.
            if len(cells) < 4 or not _is_percentage(cells[-1]):
                continue
            beneficiarios.append({
                "nombre": cells[0],
                "paterno": cells[1] if len(cells) > 1 else None,
                "materno": cells[2] if len(cells) > 2 else None,
                "parentesco": cells[3] if len(cells) > 3 else None,
                "porcentaje": cells[-1],
            })

    full_name = " ".join(x for x in [fields.get("nombre"), fields.get("paterno"), fields.get("materno")] if x)
    if full_name:
        fields["nombre_completo"] = full_name

    dob = _parse_dob(fields.get("fecha_nacimiento")) if fields.get("fecha_nacimiento") else None
    if dob:
        fields["fecha_nacimiento"] = dob

    curp = (fields.get("curp") or "").upper().strip()
    fields["curp_valid"] = bool(CURP_RE.match(curp)) if curp else False

    fields["beneficiarios"] = beneficiarios
    return fields


if __name__ == "__main__":
    import sys
    result = extract_alta(sys.argv[1])
    bens = result.pop("beneficiarios", [])
    for k, v in result.items():
        print(f"  {k:18}= {v}")
    print(f"  beneficiarios     = {len(bens)}")
    for b in bens:
        print(f"      - {b['nombre']} {b['paterno']} {b['materno']} · {b['parentesco']} · {b['porcentaje']}")
