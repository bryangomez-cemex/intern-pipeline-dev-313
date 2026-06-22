import re
import unicodedata
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation


HIGH_THRESHOLD = 90
MEDIUM_THRESHOLD = 70
EMPTY_VALUES = {"", "n/a", "na", "null", "none", "-", "--", "sin dato", "no aplica"}

STRONG_FIELD_ALIASES = {
    "intern_id": ["intern_id", "InternID", "Intern ID"],
    "employee_number": ["employee_number", "num_empleado", "NumEmpleado", "NUMERO"],
    "cemex_employee_number": ["cemex_employee_number", "num_empleado_cemex", "NumEmpleadoCemex"],
    "nss": ["nss", "NSS"],
    "rfc": ["rfc", "RFC"],
    "curp": ["curp", "CURP"],
    "email": ["email", "Email", "EMAIL", "Correo", "Correo Practicante", "E-mail"],
    "user_id": ["user_id", "USERID"],
    "sap_user_id": ["sap_user_id", "USERIDSAP"],
    "position_code": ["position_code", "CODPOS"],
    "job_code": ["job_code", "CVEPTO"],
    "unique_position_number": ["unique_position_number", "Numero Puesto", "Número Puesto", "numero_unico_puesto"],
    "requisition_id": ["requisition_id", "requisicion_id", "requisition"],
}

SECONDARY_FIELD_ALIASES = {
    "full_name": ["full_name", "NombreCompleto", "Nombre Completo", "Full Name", "Name", "NOMBRE"],
    "first_name": ["first_name", "Nombre", "First Name"],
    "paternal_last_name": ["paternal_last_name", "Paterno", "Apellido Paterno"],
    "maternal_last_name": ["maternal_last_name", "Materno", "Apellido Materno"],
    "start_date": ["start_date", "FechadeIngreso", "Fecha de Ingreso", "Start Date", "Fecha Inicio"],
    "end_date": ["end_date", "FechaContratoVence", "Fecha Fin", "End Date", "Vencimiento"],
    "manager": ["manager", "JefeInmediato", "NOMBREJEFE", "GERENTENOMBRE", "GERENCIANOMBRE"],
    "personnel_lead": ["personnel_lead", "JEFEDEPERSONAL", "ASESOR RRHH HC"],
    "cc_hc": ["cc_hc", "CC HC", "CC", "Centro de Costo", "Cost Center", "CCOPERATIVO"],
    "oi_hc": ["oi_hc", "OI HC", "OI", "Orden Interna", "Internal Order", "ORDENINTERNA"],
    "company": ["company", "CIA HC", "CIASTR", "RazonSocial", "RAZON SOCIAL HC"],
    "company_code": ["company_code", "CIA"],
    "location": ["location", "UBICACION", "UBICACIÓN HC"],
    "location_state": ["location_state", "EDOUBICACION", "ESTADO UBICACIÓN HC"],
    "vp_hc": ["vp_hc", "VP HC", "VP", "VICEPRESIDENCIA"],
    "area": ["area", "Area", "Área", "REGIONAREA", "GERENCIA"],
    "region_rh": ["region_rh", "RegionRH", "Region RH"],
    "salary": ["salary", "SalarioMensual", "Importe", "ImporteTotal"],
}

STRONG_WEIGHTS = {
    "intern_id": 100,
    "requisition_id": 100,
    "unique_position_number": 98,
    "position_code": 95,
    "job_code": 90,
    "curp": 95,
    "rfc": 92,
    "nss": 92,
    "employee_number": 94,
    "cemex_employee_number": 94,
    "email": 90,
    "user_id": 88,
    "sap_user_id": 88,
}

SECONDARY_WEIGHTS = {
    "full_name": 35,
    "start_date": 10,
    "end_date": 10,
    "manager": 5,
    "personnel_lead": 4,
    "cc_hc": 5,
    "oi_hc": 5,
    "company": 4,
    "company_code": 4,
    "location": 3,
    "location_state": 2,
    "vp_hc": 5,
    "area": 4,
    "region_rh": 3,
    "salary": 3,
}


def normalize_value(value, value_type=None):
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, (datetime, date)):
        return normalize_date(value) if value_type == "date" else value.isoformat()

    raw = str(value).strip()
    if raw.lower() in EMPTY_VALUES:
        return None
    if value_type == "date":
        return normalize_date(raw)
    if value_type == "name":
        return normalize_name(raw)
    if value_type == "email":
        return normalize_email(raw)
    if value_type in {"money", "currency", "salary"}:
        return normalize_money(raw)

    normalized = strip_accents(raw)
    normalized = re.sub(r"\s+", " ", normalized.replace("\n", " ").replace("\r", " ").replace("\t", " ")).strip()
    if value_type in {"id", "identifier"}:
        return re.sub(r"[^A-Z0-9]", "", normalized.upper()) or None
    return normalized.upper() or None


def normalize_name(value):
    if value is None:
        return None
    raw = str(value).strip()
    if raw.lower() in EMPTY_VALUES:
        return None
    if "," in raw:
        left, right = raw.split(",", 1)
        raw = f"{right.strip()} {left.strip()}"
    normalized = strip_accents(raw)
    normalized = re.sub(r"[^A-Za-z0-9 ]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().upper()
    return normalized or None


def normalize_email(value):
    normalized = strip_accents(str(value)).strip().lower()
    normalized = re.sub(r"\s+", "", normalized)
    return normalized if normalized and normalized not in EMPTY_VALUES else None


def normalize_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    raw = str(value).strip()
    if raw.lower() in EMPTY_VALUES:
        return None
    if re.fullmatch(r"\d+(\.0)?", raw):
        serial = int(float(raw))
        if 1 <= serial <= 80000:
            return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()

    raw = raw.replace(".", "/").replace("-", "/")
    for date_format in ("%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%m/%d/%y"):
        try:
            return datetime.strptime(raw, date_format).date().isoformat()
        except ValueError:
            continue
    return normalize_value(raw)


def normalize_money(value):
    raw = str(value).strip()
    if raw.lower() in EMPTY_VALUES:
        return None
    cleaned = raw.replace("$", "").replace(",", "").replace("MXN", "").replace("mxn", "").strip()
    try:
        return str(Decimal(cleaned).quantize(Decimal("0.01")))
    except InvalidOperation:
        return normalize_value(raw)


def build_match_profile(row, entity_type="intern"):
    row = row or {}
    fields = {}
    for canonical_field, aliases in {**STRONG_FIELD_ALIASES, **SECONDARY_FIELD_ALIASES}.items():
        original = first_available(row, aliases)
        normalized = normalize_value(original, field_value_type(canonical_field))
        if normalized is None and canonical_field == "full_name":
            normalized = build_name_from_parts(row)
        if normalized is None:
            continue
        fields[canonical_field] = {
            "original": original,
            "normalized": normalized,
            "field_strength": "strong" if canonical_field in STRONG_FIELD_ALIASES else "secondary",
        }
    return {
        "entity_type": entity_type,
        "entity_id": get_entity_id(row, entity_type),
        "fields": fields,
        "original_values": {field: info["original"] for field, info in fields.items()},
    }


def find_candidate_matches(match_profile, candidates, entity_type=None):
    matches = []
    for candidate in candidates or []:
        candidate_profile = build_match_profile(candidate, entity_type or candidate.get("entity_type") or match_profile.get("entity_type"))
        scored = score_candidate(match_profile, candidate_profile)
        if scored["match_score"] > 0 or scored["match_confidence"] == "CONFLICT":
            matches.append({
                **scored,
                "matched_entity_type": candidate_profile["entity_type"],
                "matched_entity_id": candidate_profile["entity_id"],
                "candidate_profile": candidate_profile,
            })
    return sorted(matches, key=lambda item: (item["match_confidence"] == "CONFLICT", item["match_score"]), reverse=True)


def score_candidate(match_profile, candidate_profile):
    source_fields = match_profile.get("fields", {})
    candidate_fields = candidate_profile.get("fields", {})
    evidence = []
    score = 0
    method = None

    for field_name, weight in STRONG_WEIGHTS.items():
        if same_field(source_fields, candidate_fields, field_name):
            score = max(score, weight)
            method = field_name
            evidence.append(evidence_item(field_name, source_fields[field_name], candidate_fields[field_name], weight))

    for field_name, weight in SECONDARY_WEIGHTS.items():
        if same_field(source_fields, candidate_fields, field_name):
            score = min(100, score + weight)
            method = method or "secondary_fields"
            evidence.append(evidence_item(field_name, source_fields[field_name], candidate_fields[field_name], weight))

    conflicts = pairwise_conflicts(source_fields, candidate_fields)
    if names_match(source_fields, candidate_fields) and strong_ids_disagree(source_fields, candidate_fields):
        conflicts.append("Name matches, but one or more strong identifiers disagree.")
    if conflicts:
        return {
            "match_score": min(score, 69),
            "match_confidence": "CONFLICT",
            "match_method": method or "conflict_detection",
            "evidence_used": evidence,
            "needs_review": True,
            "conflict_reason": " | ".join(sorted(set(conflicts))),
        }

    confidence = match_confidence(score)
    return {
        "match_score": score,
        "match_confidence": confidence,
        "match_method": method or "no_match",
        "evidence_used": evidence,
        "needs_review": confidence != "HIGH",
        "conflict_reason": None,
    }


def resolve_best_match(match_profile, candidates, entity_type=None):
    candidate_matches = find_candidate_matches(match_profile, candidates, entity_type=entity_type)
    conflicts = detect_match_conflicts(match_profile, candidates)
    if conflicts:
        return match_result(0, "CONFLICT", "conflict_detection", entity_type or match_profile.get("entity_type"), None, [], candidate_matches[:5], True, " | ".join(conflicts))
    if not candidate_matches:
        return match_result(0, "LOW", "no_candidate", entity_type or match_profile.get("entity_type"), None, [], [], True, None)

    best = candidate_matches[0]
    alternatives = candidate_matches[1:5]
    if alternatives and best["match_confidence"] == "HIGH" and alternatives[0]["match_score"] >= best["match_score"] - 5:
        return match_result(best["match_score"], "MEDIUM", "ambiguous_high_score", best["matched_entity_type"], best["matched_entity_id"], best["evidence_used"], alternatives, True, "Multiple close candidate matches found.")
    return match_result(best["match_score"], best["match_confidence"], best["match_method"], best["matched_entity_type"], best["matched_entity_id"], best["evidence_used"], alternatives, best["needs_review"], best["conflict_reason"])


def detect_match_conflicts(match_profile, candidates):
    conflicts = []
    source_fields = match_profile.get("fields", {})
    seen_nss = {}
    for candidate in candidates or []:
        candidate_profile = build_match_profile(candidate, candidate.get("entity_type") or match_profile.get("entity_type"))
        candidate_fields = candidate_profile.get("fields", {})
        conflicts.extend(pairwise_conflicts(source_fields, candidate_fields))
        nss = normalized_field(candidate_fields, "nss")
        if nss:
            prior = seen_nss.get(nss)
            if prior and prior != candidate_profile["entity_id"]:
                conflicts.append("Same NSS appears in multiple candidate records.")
            seen_nss[nss] = candidate_profile["entity_id"]
    return sorted(set(conflicts))


def match_confidence(score):
    if score >= HIGH_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def strip_accents(value):
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def first_available(row, aliases):
    for alias in aliases:
        if alias in row:
            return row.get(alias)
    normalized_row = {normalize_key(key): value for key, value in row.items()}
    for alias in aliases:
        value = normalized_row.get(normalize_key(alias))
        if value is not None:
            return value
    return None


def normalize_key(value):
    return re.sub(r"[^a-z0-9]", "", strip_accents(str(value)).lower())


def field_value_type(field_name):
    if field_name in {"full_name", "first_name", "paternal_last_name", "maternal_last_name", "manager", "personnel_lead"}:
        return "name"
    if field_name in {"start_date", "end_date"}:
        return "date"
    if field_name == "email":
        return "email"
    if field_name == "salary":
        return "salary"
    if field_name in STRONG_FIELD_ALIASES:
        return "identifier"
    return None


def build_name_from_parts(row):
    parts = [
        first_available(row, SECONDARY_FIELD_ALIASES["first_name"]),
        first_available(row, SECONDARY_FIELD_ALIASES["paternal_last_name"]),
        first_available(row, SECONDARY_FIELD_ALIASES["maternal_last_name"]),
    ]
    return normalize_name(" ".join(str(part) for part in parts if part))


def get_entity_id(row, entity_type):
    candidates = {
        "intern": ["intern_id"],
        "new_hire": ["intern_id", "hire_id"],
        "requisition": ["requisition_id"],
        "position": ["position_id", "position_code", "unique_position_number", "CODPOS"],
    }.get(entity_type, [])
    for field_name in candidates + ["entity_id", "id", "intern_id", "requisition_id", "position_id"]:
        value = row.get(field_name)
        if value:
            return str(value)
    return None


def normalized_field(fields, field_name):
    field = fields.get(field_name)
    return field.get("normalized") if field else None


def evidence_item(field_name, source_field, candidate_field, score_weight):
    return {
        "field": field_name,
        "source_original": source_field.get("original"),
        "source_normalized": source_field.get("normalized"),
        "candidate_original": candidate_field.get("original"),
        "candidate_normalized": candidate_field.get("normalized"),
        "score_weight": score_weight,
    }


def pairwise_conflicts(source_fields, candidate_fields):
    conflicts = []
    if same_field(source_fields, candidate_fields, "curp") and different_field(source_fields, candidate_fields, "rfc"):
        conflicts.append("Same CURP but different RFC.")
    if same_field(source_fields, candidate_fields, "email") and different_any(source_fields, candidate_fields, ["employee_number", "cemex_employee_number"]):
        conflicts.append("Same EMAIL but different employee number.")
    if same_field(source_fields, candidate_fields, "nss") and not names_match(source_fields, candidate_fields):
        conflicts.append("Same NSS appears to belong to different people.")
    if same_field(source_fields, candidate_fields, "unique_position_number") and different_field(source_fields, candidate_fields, "intern_id"):
        conflicts.append("Same position number is linked to a different new hire/intern.")
    if same_field(source_fields, candidate_fields, "position_code") and different_field(source_fields, candidate_fields, "intern_id"):
        conflicts.append("Same CODPOS is linked to a different active intern/new hire.")
    return conflicts


def same_field(source_fields, candidate_fields, field_name):
    source_value = normalized_field(source_fields, field_name)
    candidate_value = normalized_field(candidate_fields, field_name)
    return bool(source_value and candidate_value and source_value == candidate_value)


def different_field(source_fields, candidate_fields, field_name):
    source_value = normalized_field(source_fields, field_name)
    candidate_value = normalized_field(candidate_fields, field_name)
    return bool(source_value and candidate_value and source_value != candidate_value)


def different_any(source_fields, candidate_fields, field_names):
    return any(different_field(source_fields, candidate_fields, field_name) for field_name in field_names)


def strong_ids_disagree(source_fields, candidate_fields):
    return any(different_field(source_fields, candidate_fields, field_name) for field_name in STRONG_FIELD_ALIASES)


def names_match(source_fields, candidate_fields):
    source_name = normalized_field(source_fields, "full_name") or composed_name(source_fields)
    candidate_name = normalized_field(candidate_fields, "full_name") or composed_name(candidate_fields)
    return bool(source_name and candidate_name and source_name == candidate_name)


def composed_name(fields):
    parts = [
        normalized_field(fields, "first_name"),
        normalized_field(fields, "paternal_last_name"),
        normalized_field(fields, "maternal_last_name"),
    ]
    return normalize_name(" ".join(part for part in parts if part))


def match_result(match_score, match_confidence, match_method, matched_entity_type, matched_entity_id, evidence_used, alternative_matches, needs_review, conflict_reason):
    return {
        "match_score": match_score,
        "match_confidence": match_confidence,
        "match_method": match_method,
        "matched_entity_type": matched_entity_type,
        "matched_entity_id": matched_entity_id,
        "evidence_used": evidence_used,
        "alternative_matches": summarize_alternatives(alternative_matches),
        "needs_review": needs_review,
        "conflict_reason": conflict_reason,
    }


def summarize_alternatives(candidate_matches):
    return [{
        "matched_entity_type": candidate.get("matched_entity_type"),
        "matched_entity_id": candidate.get("matched_entity_id"),
        "match_score": candidate.get("match_score"),
        "match_confidence": candidate.get("match_confidence"),
        "match_method": candidate.get("match_method"),
        "conflict_reason": candidate.get("conflict_reason"),
    } for candidate in (candidate_matches or [])]
