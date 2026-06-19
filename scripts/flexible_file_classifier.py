import unicodedata

import pandas as pd


ALLOWED_EXTENSIONS = {"pdf", "xlsx", "csv", "png", "jpg", "jpeg"}

CANONICAL_FIELD_ALIASES = {
    "intern_id": ["InternID", "Intern ID"],
    "employee_number": ["NumEmpleado", "Numero Empleado", "Employee Number"],
    "cemex_employee_number": ["NumEmpleadoCemex", "Numero Empleado Cemex", "CEMEX Employee Number"],
    "email": ["Email", "Correo", "Correo Practicante", "E-mail"],
    "full_name": ["NombreCompleto", "Nombre Completo", "Full Name", "Name"],
    "first_name": ["Nombre", "First Name"],
    "paternal_last_name": ["Paterno", "Apellido Paterno"],
    "maternal_last_name": ["Materno", "Apellido Materno"],
    "curp": ["CURP"],
    "rfc": ["RFC"],
    "nss": ["NSS"],
    "university": ["Universidad", "University"],
    "career": ["Carrera", "Career", "Major"],
    "semester": ["Semestre", "Semester"],
    "area": ["Area", "Área"],
    "position": ["Puesto", "Position"],
    "start_date": ["FechadeIngreso", "Fecha de Ingreso", "Start Date", "Fecha Inicio"],
    "end_date": ["FechaContratoVence", "Fecha Fin", "End Date", "Vencimiento"],
    "status": ["Estatus", "Status"],
    "oi_hc": ["OI HC", "OI", "Orden Interna", "Internal Order"],
    "cc_hc": ["CC HC", "CC", "Centro de Costo", "Cost Center"],
    "vp_hc": ["VP HC", "VP", "Vicepresidencia"],
    "region_rh": ["RegionRH", "Region RH", "HR Region"],
    "manager": ["JefeInmediato", "Jefe Inmediato", "Manager", "Supervisor", "Jefe"],
    "company": ["CIA HC", "RazonSocial", "RAZON SOCIAL HC", "Company", "Compania", "Compañía"],
    "salary": ["SalarioMensual", "Salary", "Sueldo", "Salario"],
    "gender": ["Sexo", "Gender"],
    "age": ["Edad", "Age"],
}

CANONICAL_TO_LEGACY_COLUMNS = {
    "employee_number": "NumEmpleado",
    "cemex_employee_number": "NumEmpleadoCemex",
    "nss": "NSS",
    "rfc": "RFC",
    "curp": "CURP",
    "first_name": "Nombre",
    "paternal_last_name": "Paterno",
    "maternal_last_name": "Materno",
    "full_name": "NombreCompleto",
    "position": "Puesto",
    "manager": "JefeInmediato",
    "salary": "SalarioMensual",
    "cc_hc": "CC HC",
    "vp_hc": "VP HC",
    "region_rh": "RegionRH",
    "oi_hc": "OI HC",
    "company": "CIA HC",
    "area": "Area",
    "university": "Universidad",
    "career": "Carrera",
    "semester": "Semestre",
    "start_date": "FechadeIngreso",
    "end_date": "FechaContratoVence",
    "status": "Estatus",
    "gender": "Sexo",
    "age": "Edad",
}


def normalize_header(value):
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))

    return " ".join(
        normalized
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
        .replace("_", " ")
        .replace("-", " ")
        .strip()
        .lower()
        .split()
    )


ALIAS_LOOKUP = {}

for canonical_field, aliases in CANONICAL_FIELD_ALIASES.items():
    for alias in aliases:
        ALIAS_LOOKUP[normalize_header(alias)] = canonical_field


def read_tabular_file(local_path, extension):
    sheet_names = []

    if extension == "xlsx":
        excel_file = pd.ExcelFile(local_path)
        sheet_names = excel_file.sheet_names
        df = pd.read_excel(local_path)
    elif extension == "csv":
        df = pd.read_csv(local_path)
    else:
        return None, sheet_names

    df.columns = [str(col).replace("\n", " ").replace("\r", " ").replace("\t", " ").strip() for col in df.columns]
    df = df.dropna(how="all")

    return df, sheet_names


def map_dataframe_columns(df):
    if df is None:
        return []

    mapped_columns = []

    for index, column in enumerate(df.columns, start=1):
        source_column_name = str(column).strip()
        normalized_column_name = normalize_header(source_column_name)
        canonical_field_name = ALIAS_LOOKUP.get(normalized_column_name)

        mapped_columns.append({
            "sheet_name": None,
            "ordinal_position": index,
            "source_column_name": source_column_name,
            "normalized_column_name": normalized_column_name,
            "canonical_field_id": canonical_field_name,
            "canonical_field_name": canonical_field_name,
            "source_profile": "flexible_file_classifier" if canonical_field_name else None,
            "mapping_confidence": 1.0 if canonical_field_name else None,
        })

    return mapped_columns


def get_document_type_id(file_name, extension):
    name = file_name.lower()

    if extension in {"xlsx", "csv"}:
        return "DOC004"
    if "cv" in name or "resume" in name or "curriculum" in name:
        return "DOC006"
    if "nda" in name or "confidencial" in name:
        return "DOC007"
    if "acta" in name or "nacimiento" in name:
        return "DOC008"
    if "offer" in name or "oferta" in name:
        return "DOC009"
    if "forms" in name or "onboarding" in name:
        return "DOC010"
    if "convenio" in name:
        return "DOC001"
    if "identificacion" in name or "ine" in name or "id" in name:
        return "DOC002"
    if "comprobante" in name or "escolar" in name or "universidad" in name or "plan" in name:
        return "DOC003"
    if "coparmex" in name:
        return "DOC005"

    return "DOC999"


def detect_file_profile(file_name, extension, sheet_names=None, columns=None):
    name = file_name.lower()
    normalized_columns = {normalize_header(col) for col in (columns or [])}
    canonical_fields = {ALIAS_LOOKUP[col] for col in normalized_columns if col in ALIAS_LOOKUP}
    sheet_text = " ".join(sheet_names or []).lower()
    text = f"{name} {sheet_text}"

    if extension == "xlsx":
        suffix_profile = "excel"
    elif extension == "csv":
        suffix_profile = "csv"
    elif extension == "pdf":
        return "generic_pdf"
    elif extension in {"png", "jpg", "jpeg"}:
        return "generic_image"
    else:
        return "unknown_file"

    if any(token in text for token in ["requisition", "requisicion", "requisición", "alta", "baja", "extension", "extendimiento", "posicion", "posición", "position"]):
        return "requisition_excel" if extension == "xlsx" else "generic_csv"

    if any(token in text for token in ["accepted", "accepted hires", "new hire", "new_hire", "hires", "contratados", "ingresos"]):
        return f"accepted_hires_{suffix_profile}"

    if any(token in text for token in ["current", "actual", "actuales", "activos", "practicantes actuales", "current interns", "current_intern"]):
        return f"current_interns_{suffix_profile}"

    if {"full_name", "start_date", "end_date"} & canonical_fields:
        return f"accepted_hires_{suffix_profile}" if extension == "xlsx" else "generic_csv"

    if {"employee_number", "cemex_employee_number", "status"} & canonical_fields and {"end_date", "oi_hc", "cc_hc"} & canonical_fields:
        return f"current_interns_{suffix_profile}"

    return "generic_excel" if extension == "xlsx" else "generic_csv"


def is_row_processable(file_profile_id):
    return file_profile_id in {
        "requisition_excel",
        "accepted_hires_excel",
        "accepted_hires_csv",
        "current_interns_excel",
        "current_interns_csv",
        "generic_excel",
        "generic_csv",
    }


def classification_confidence(file_profile_id, extension, mapped_columns, document_type_id):
    mapped_count = len([col for col in mapped_columns if col.get("canonical_field_name")])

    if file_profile_id in {"accepted_hires_excel", "current_interns_excel", "requisition_excel"}:
        return 0.9 if mapped_count >= 4 else 0.72

    if file_profile_id in {"generic_excel", "generic_csv"}:
        return 0.65 if mapped_count >= 3 else 0.45

    if file_profile_id in {"generic_pdf", "generic_image"}:
        return 0.75 if document_type_id != "DOC999" else 0.45

    return 0.3


def classify_file(file_name, extension, mime_type, df=None, sheet_names=None):
    extension = extension.lower().replace(".", "")
    mapped_columns = map_dataframe_columns(df)
    columns = list(df.columns) if df is not None else []
    file_profile_id = detect_file_profile(file_name, extension, sheet_names, columns)
    document_type_id = get_document_type_id(file_name, extension)
    confidence = classification_confidence(file_profile_id, extension, mapped_columns, document_type_id)

    profile_process_map = {
        "requisition_excel": "requisition",
        "accepted_hires_excel": "new_hire",
        "accepted_hires_csv": "new_hire",
        "current_interns_excel": "current_intern_sync",
        "current_interns_csv": "current_intern_sync",
        "generic_excel": "document_refresh",
        "generic_csv": "document_refresh",
        "generic_pdf": "document_refresh",
        "generic_image": "document_refresh",
        "unknown_file": "document_refresh",
    }

    row_processable = is_row_processable(file_profile_id)
    needs_review = file_profile_id == "unknown_file" or confidence < 0.5

    if file_profile_id == "unknown_file":
        reason = "Unknown file type or weak profile match; stored for manual review."
    elif row_processable:
        reason = "File profile detected from filename, sheet names, and mapped columns."
    else:
        reason = "Document profile detected from extension and filename keywords."

    return {
        "file_profile_id": file_profile_id,
        "process_type_id": profile_process_map.get(file_profile_id, "document_refresh"),
        "document_type_id": document_type_id,
        "row_processable": row_processable,
        "needs_review": needs_review,
        "classification_confidence": confidence,
        "classification_reason": reason,
        "sheet_names": ", ".join(sheet_names or []),
        "detected_column_count": len(columns),
        "detected_columns": mapped_columns,
        "mime_type": mime_type,
    }


def normalize_row_to_legacy(row, detected_columns):
    legacy_row = dict(row)

    for column_info in detected_columns:
        canonical_field_name = column_info.get("canonical_field_name")
        source_column_name = column_info.get("source_column_name")
        legacy_column_name = CANONICAL_TO_LEGACY_COLUMNS.get(canonical_field_name)

        if not legacy_column_name:
            continue

        if legacy_column_name not in legacy_row or pd.isna(legacy_row.get(legacy_column_name)):
            legacy_row[legacy_column_name] = row.get(source_column_name)

    return legacy_row
