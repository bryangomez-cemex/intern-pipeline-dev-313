# Requisición → new-hire workflow — data model design

Status: design draft (no code yet). Grounded in `Requisición Practicante.docx`,
`Data_Dictionary_Requisiciones_Practicantes_v1.xlsx` (57 fields, 32 validation
rules), `Plantilla_Practicantes_Completa.xlsx`, and the existing Azure SQL schema.

## 1. The flow we are modeling

1. A **requisición** (`.docx`) is sent in → system parses it → creates a **Position**
   with a **Position ID** (`REQ-YYYY-0001`) and validates the requisición.
2. **New-hire-package** files (NDA, CV, ID, etc.) are sent in → stored and linked
   to a Position / candidate, completeness checked.
3. HR sends a **new-hire list** (spreadsheet) → each row is **matched to a Position**
   by Position ID → cross-validated against the requisición.
4. Clean match → assemble package + send the new hire "congrats + next steps".
   Any failure → **return the email to the sender** explaining why.

## 2. Entities (data dictionary ↔ existing SQL)

The data dictionary defines 4 lists. They map onto existing SQL tables, mostly with
columns to add:

| Entity (data dict) | SQL table | Key | State |
|---|---|---|---|
| Requisiciones (Positions) | `dim_requisitions` | `requisition_id` = **REQ-YYYY-0001** | exists; extend |
| Practicantes (Candidates) | `dim_interns` | `intern_id` (adopt **PRA-YYYY-0001**) | exists; extend |
| Catálogo OI-CC-Sociedad | new `dim_oi_cc_sociedad` | composite (OI+CC+Sociedad) | build |
| Validaciones Errores | `fact_validations` | `validation_id` | exists |

### Position ID is the spine
- Generated when a requisición is ingested (`REQ-YYYY-0001`).
- Every `dim_interns` row links to exactly one `dim_requisitions` via a new
  `requisition_id` FK. A requisición has `number_of_positions`; matched candidates fill them.

## 3. The matching key — DECIDED: carry REQ-id explicitly (option A)

`Plantilla_Practicantes_Completa.xlsx` (HR's new-hire list) has **no requisition/
position ID column** — only `Puesto` (free text), `VP HC`, `Area`, `JefeInmediato`,
`Carrera`, etc. So the Position ID must travel with the data.

**Decision:** the `REQ-YYYY-0001` Position ID is carried explicitly and used as the
deterministic join key. Two accepted ways to supply it (either works):
- HR adds an `ID Requisición` column to their new-hire export, or
- the Position ID is included in the intake email subject, e.g. `[INTERN][REQ-2026-0001]`.

The matching engine joins `dim_interns.requisition_id` → `dim_requisitions.requisition_id`
on this value. If the ID is missing or unknown on a new-hire row, that row is **returned
to the sender** ("falta el ID de requisición") rather than guessed. Fuzzy matching on
`Puesto + VP + Area + Carrera` is kept only as an optional low-confidence hint for the
review queue, never as the authoritative match.

Action item (process, not code): tell whoever produces the HR list to include the
Position ID (column or email subject) starting now.

## 4. Document parsing (rule-based, per your choice)

The requisición `.docx` uses consistent labels, so label→field extraction works:

| Label in document | Field |
|---|---|
| Nombre del Puesto | `puesto` |
| Vicepresidencia: | `vp` |
| Dirección: | `direccion` |
| Región / área: | `region_area` |
| Asesor Recursos Humanos: | `asesor_rh` |
| Jefe directo: | `manager_name` |
| Carrera (s): | `carrera_requerida` |
| Semestre (s): | `semestre_requerido` |
| Disponibilidad de horario: | `disponibilidad_horario` |
| Periodo de estadía en Cemex: | `periodo_estadia` |
| Fecha inicio y fecha de término: | `fecha_inicio_solicitada` / `fecha_termino_solicitada` (parse range) |
| (section bodies) | `descripcion_proyecto`, `retos`, `responsabilidades`, `entregables`, `habilidades` |

Caveat of rule-based: brittle to label/format changes. When an expected label is
missing, mark the requisición **Needs Review** rather than guessing. `.docx` must
also be added to the allowed extensions (today it is skipped) plus a small docx text
extractor (unzip `word/document.xml`).

## 5. Validation (rule-based, from the 32 Reglas Validación)

Seed `dim_validation_rules` with the data dictionary's 32 rules. Each carries:
`field(s)`, `check`, `severidad` (Alta / Media / Crítica), and **`acción automática`**:

| Acción automática | System behavior |
|---|---|
| Regresar a solicitante | bounce email to the sender with the rule message |
| Corrección requerida | log error, request a corrected resend |
| Bloquear aprobación | hard-stop; cannot become an approved Position |
| Revisión RH / Finanzas | route to a manual review queue |
| Revisión duplicado | flag possible duplicate (e.g. email already active) |

Examples already specified: R004 semestre 1–12, R006 fecha término > inicio, R010
email format, R011 duplicate active email, R016–R020 OI/CC/Sociedad must exist &
be active in the catalog, R021 monto > 0.

## 6. Outcomes / orchestration

- **Capture the sender's email at intake** (currently discarded). Needed for the
  "return the email explaining why" step. Store on `fact_files` / a small intake table.
- **Requisición** clean → create Position (`status` En revisión → Aprobada). Failing
  a "Regresar a solicitante" rule → reply to sender with the collected messages.
- **New-hire-package** → store docs per Position/candidate, set `documentos_completos`.
- **HR list** → match each row to a Position (§3) → cross-validate the row against the
  requisición (carrera, semestre, fechas, OI/CC/Sociedad consistent) →
  clean → assemble package + send new-hire "congrats + next steps";
  mismatch/inconsistent → return to HR with reasons.

## 7. Schema deltas to build

- `ALTER dim_requisitions`: add ~20 content fields (§4) + `carrera_requerida`,
  `semestre_requerido`, `tipo_requisicion`, `prioridad`, `fecha_solicitud`,
  `motivo_rechazo`, `documentos_completos`, `convenio_requerido`.
- `ALTER dim_interns`: add `requisition_id` (FK), `email_personal`, `telefono`,
  `campus`, `fecha_nacimiento`.
- `NEW dim_oi_cc_sociedad` catalog + seed.
- Seed `dim_validation_rules` with the 32 rules.
- Add `sender_email` capture at intake.
- Add `.docx` ingestion + docx text extractor.

## 8. Build phases (mapped to this model)

1. **Requisición → Position.** `.docx` ingest → parse → create `dim_requisitions`
   row with `REQ-YYYY-0001` + requisición validation + sender bounce.
2. **New-hire-package.** Store the document bundle per Position/candidate; completeness.
3. **HR list → match.** Ingest HR spreadsheet → match to Position (§3) → cross-validate.
4. **Orchestration.** Congrats-send on clean match; return-to-sender on failure.

Each phase produces observable SQL rows, consistent with the rest of the pipeline.

## 9. Full onboarding lifecycle (the real process)

The requisición is only stage 1. The complete flow, taken from the real CEMEX emails
and document sets:

| Stage | Inbound | System does | Outbound email |
|---|---|---|---|
| A. Requisición | requisición `.docx` | parse → create Position `REQ-id`, validate | return-to-sender if invalid |
| B. Welcome 1 | (a candidate is assigned to a Position) | prepare request | "Bienvenida – Trámite Convenio": ask for personal data + docs, **attach the Coparmex alta Excel** |
| C. Candidate docs | new hire emails: alta Excel (filled), CURP, acta de nacimiento, constancia de estudios, identificación, foto | classify each doc **by content** (names/types vary), extract fields, **cross-validate**, store **only if correct** | return-to-sender listing what's missing/wrong |
| D. Convenio prep | **HR** emails convenio + póliza + Acuerdo de Confidencialidad to the system | match to the known candidate (name+email already known from C), store | forward to new hire: "Bienvenida – Documentos" with the 3 files |
| E. Signed docs | new hire returns `ConvenioAltaFirmado.pdf`, `AcuerdoConfidencialidad2026.pdf` (named `Nombre_Apellido_Documento`) | same pipeline: validate naming/format/completeness | return-to-sender if wrong |
| F. Done | all stages clean | finalize onboarding | notify **HR + Coparmex** (placeholders for now) |

Email subjects to template (`dim_email_templates`):
- Welcome 1: `¡Te damos la bienvenida a Cemex! Trámite Convenio – 'Summer Internship Program'`
- Welcome 2: `¡Te damos la bienvenida a Cemex! Documentos – 'Summer Internship Program'`

### New requirements this lifecycle introduces
- **Content-based classification.** Inbound docs have arbitrary names/types
  (`Pasaporte - Bryan.pdf`, `Curp - Bryan Gomez.pdf`, `EnrollmentCertificate-…pdf`,
  `image001.png`). Classify by what's *inside*, not the filename.
- **Cross-file validation + field merge.** Extract from every document and verify
  consistency, then merge into one candidate record:
  - CURP on the alta Excel == CURP on the CURP PDF;
  - carrera/universidad on the alta == constancia de estudios == the requisición;
  - identity (nombre, nacionalidad) == passport/ID;
  - beneficiarios + address come from the alta; graduation date from the constancia.
  Store a field **only if** it is present and consistent; otherwise flag and return.
- **Stages D/E need no Position-ID matching** — the candidate (name+email) is already
  known from stage C, so those rounds bind by candidate identity.
- PDF/image extraction is harder than Excel with rule-based parsing: CURP is a fixed
  18-char regex (reliable); passport/constancia are semi-structured (extract what's
  reliably patterned, else mark "needs review").

## 10. The alta format (Coparmex) — fields the candidate fills

From `ALTA PRACTICANTE` / `NA FORMATO PARA ALTA DE PRACTICANTE COPARMEX.xlsx`:
- Datos del practicante: nombres, apellido paterno/materno, sexo, estado civil,
  nacionalidad, matrícula, carrera, grado, domicilio (calle/número/colonia/población/
  estado/CP), teléfono, mail, fecha de nacimiento, **CURP** (obligatorio – banco).
- Datos de la escuela: nombre, domicilio, teléfono.
- Datos de la empresa (CEMEX llena): empresa, domicilio, fecha de inicio, meses,
  apoyo mensual, jefe directo, puesto, horario, departamento.
- Beneficiarios: nombre + parentesco + % (1..n rows).

These map to `dim_interns` (extended) and a new `fact_intern_beneficiaries` child table.

## 11. Revised build phases (reflecting the full lifecycle)

1. **Requisición → Position.** `.docx` ingest + parse + `dim_requisitions` row +
   `REQ-id` + requisición validation + sender bounce. (foundational — start here)
2. **Candidate docs (stage C).** Content-based classification + per-document field
   extraction + cross-file validation/merge into `dim_interns` + beneficiaries.
3. **Lifecycle emails (B, D, F).** Welcome 1 (request + alta attach), Welcome 2
   (forward HR's convenio/póliza/acuerdo), final HR+Coparmex notification.
4. **Signed-docs round (stage E)** + status/lifecycle tracking end to end.
