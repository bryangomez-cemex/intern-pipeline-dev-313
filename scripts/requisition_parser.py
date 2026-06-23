"""
Rule-based parser for a requisición de practicante (.docx).

Extracts the structured fields from a free-text Word requisición using the
document's consistent labels and section headings. Returns a dict of fields plus
a needs_review flag + parse_notes when expected content is missing — the pipeline
should never silently guess.
"""

import re
import zipfile
from datetime import date


SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

# "Label: value" on the same line. Order matters — list the more specific label
# first (e.g. "carrera (s)" before "carrera") so it wins the prefix match.
INLINE_LABELS = [
    ("vicepresidencia", "vp"),
    ("dirección", "direccion"), ("direccion", "direccion"),
    ("región / área", "region_area"), ("region / area", "region_area"),
    ("asesor recursos humanos", "asesor_rh"),
    ("jefe directo", "manager_name"),
    ("semestre (s)", "semestre_requerido"), ("semestre", "semestre_requerido"),
    ("carrera (s)", "carrera_requerida"), ("carrera", "carrera_requerida"),
    ("disponibilidad de horario", "disponibilidad_horario"),
    ("periodo de estadía en cemex", "periodo_estadia"),
    ("periodo de estadia en cemex", "periodo_estadia"),
    ("fecha inicio y fecha de término", "fechas_raw"),
    ("fecha inicio y fecha de termino", "fechas_raw"),
]

# Heading on its own line; the value is the following paragraph(s) until the next
# known heading / inline label / ignored heading.
SECTION_HEADINGS = [
    ("nombre del puesto", "puesto"),
    ("descripción del proyecto", "descripcion_proyecto"),
    ("descripcion del proyecto", "descripcion_proyecto"),
    ("retos que implican para el estudiante", "retos"),
    ("principales responsabilidades y actividades por realizar", "responsabilidades"),
    ("entregables del practicante que demuestran su aprendizaje", "entregables"),
    ("habilidades, competencias y/o conocimientos requeridos", "habilidades"),
]

IGNORE_HEADINGS = {
    "acerca de cemex",
    "información de la vacante", "informacion de la vacante",
    "candidato /a", "candidato/a",
    "cemex diversidad e inclusión", "cemex diversidad e inclusion",
}

REQUIRED_FIELDS = ["puesto", "vp", "carrera_requerida", "semestre_requerido"]


def extract_paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")

    paragraphs = []
    for block in re.split(r"</w:p>", xml):
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", block))
        text = re.sub(r"<[^>]+>", "", text).replace("\xa0", " ").strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _norm(value):
    return value.lower().strip()


def parse_spanish_date(token):
    if not token:
        return None
    parts = token.strip().lower().replace(",", " ").replace(".", " ").split()
    month = day = year = None
    for word in parts:
        if word in SPANISH_MONTHS:
            month = SPANISH_MONTHS[word]
        elif word.isdigit():
            number = int(word)
            if number >= 1900:
                year = number
            elif 1 <= number <= 31 and day is None:
                day = number
    if month and day and year:
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def parse_date_range(raw):
    if not raw:
        return None, None
    parts = re.split(r"\s*[–—-]\s*|\s+a\s+", raw)
    if len(parts) >= 2:
        return parse_spanish_date(parts[0]), parse_spanish_date(parts[1])
    return parse_spanish_date(raw), None


def parse_requisition_docx(docx_path):
    paragraphs = extract_paragraphs(docx_path)
    fields = {}
    section_field = None
    section_buffer = []

    def flush_section():
        nonlocal section_field, section_buffer
        if section_field and section_buffer:
            fields[section_field] = " ".join(section_buffer).strip()
        section_field = None
        section_buffer = []

    for para in paragraphs:
        norm = _norm(para)

        inline_match = next(((lbl, fld) for lbl, fld in INLINE_LABELS if norm.startswith(lbl)), None)
        if inline_match:
            flush_section()
            label, field = inline_match
            fields[field] = para[len(label):].lstrip(" :\t").strip()
            continue

        heading_match = next(((lbl, fld) for lbl, fld in SECTION_HEADINGS if norm == lbl or norm.startswith(lbl)), None)
        if heading_match:
            flush_section()
            section_field = heading_match[1]
            continue

        if norm in IGNORE_HEADINGS:
            flush_section()
            continue

        if section_field:
            section_buffer.append(para)

    flush_section()

    fecha_inicio, fecha_termino = parse_date_range(fields.pop("fechas_raw", None))
    if fecha_inicio:
        fields["fecha_inicio_solicitada"] = fecha_inicio
    if fecha_termino:
        fields["fecha_termino_solicitada"] = fecha_termino

    missing = [f for f in REQUIRED_FIELDS if not fields.get(f)]
    fields["needs_review"] = bool(missing)
    fields["parse_notes"] = ("missing required: " + ", ".join(missing)) if missing else None

    return fields


if __name__ == "__main__":
    import sys
    result = parse_requisition_docx(sys.argv[1])
    for key, value in result.items():
        shown = value if not isinstance(value, str) or len(value) <= 90 else value[:90] + "…"
        print(f"{key:28} = {shown}")
