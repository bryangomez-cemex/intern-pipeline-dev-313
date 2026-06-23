"""
Phase 1 of the requisición workflow: turn a requisición .docx into a Position.

Parses the document (rule-based), generates a Position ID (REQ-YYYY-0001), and
inserts a dim_requisitions row. Marks needs_review when required fields are absent.
"""

import os
import sys
from datetime import datetime, UTC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import azure_clients
from requisition_parser import parse_requisition_docx


# Parsed fields that map 1:1 onto dim_requisitions columns.
REQUISITION_FIELD_COLUMNS = [
    "puesto", "vp", "direccion", "region_area", "asesor_rh", "manager_name",
    "carrera_requerida", "semestre_requerido", "disponibilidad_horario",
    "periodo_estadia", "fecha_inicio_solicitada", "fecha_termino_solicitada",
    "descripcion_proyecto", "retos", "responsabilidades", "entregables",
    "habilidades", "needs_review", "parse_notes",
]


def generate_requisition_id(cursor):
    prefix = f"REQ-{datetime.now(UTC).year}-"
    cursor.execute(
        "SELECT MAX(requisition_id) FROM dim_requisitions WHERE requisition_id LIKE ?",
        prefix + "%",
    )
    last = cursor.fetchone()[0]
    next_number = 0
    if last:
        try:
            next_number = int(str(last).split("-")[-1])
        except ValueError:
            next_number = 0
    return f"{prefix}{next_number + 1:04d}"


def insert_requisition(cursor, requisition_id, fields, source_container=None, source_blob_name=None):
    data = {
        "requisition_id": requisition_id,
        "requisition_type": "Alta",
        "process_type_id": "PT006",  # Requisicion Nuevo Puesto
        "source_container": source_container,
        "source_blob_name": source_blob_name,
    }
    for column in REQUISITION_FIELD_COLUMNS:
        if column in fields:
            data[column] = fields[column]

    columns = list(data.keys())
    column_list = ", ".join(f"[{c}]" for c in columns)
    placeholders = ", ".join("?" for _ in columns)
    cursor.execute(
        f"INSERT INTO dim_requisitions ({column_list}) VALUES ({placeholders})",
        *[data[c] for c in columns],
    )
    return requisition_id


def process_requisition_file(local_path, source_container=None, source_blob_name=None):
    fields = parse_requisition_docx(local_path)

    conn = azure_clients.get_sql_connection()
    cursor = conn.cursor()
    try:
        requisition_id = generate_requisition_id(cursor)
        insert_requisition(cursor, requisition_id, fields, source_container, source_blob_name)
        conn.commit()
        return requisition_id, fields
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    req_id, parsed = process_requisition_file(sys.argv[1])
    print(f"Created Position {req_id}")
    print(f"  puesto: {parsed.get('puesto')}")
    print(f"  needs_review: {parsed.get('needs_review')}")
