# Intern System – Behavior Reference

A complete map of what the system sends, receives, validates, and decides — so it
can be reviewed and adjusted. Use the ** knob** (config you can change) and
**decision/gap** markers to drive changes.

Last reviewed: 2026-06-26. Current email state on the live Function App:
`EMAIL_SIMULATION_MODE=false` (real sends), `RH_RECIPIENT_EMAILS` =
`bryan.gomez@ext.cemex.com`, sender
`practicantes@cca4d0a7-…azurecomm.net`.

---

## 1. How files get in (triggers & timing)

| Path | Trigger | Timing | Real email? |
|---|---|---|---|
| Function App `process_raw_upload` | Event Grid on blob create in `raw-uploads/` | Near-instant | **Yes** |
| GitHub cron `mvp-ingestion.yml` | `*/5 * * * *` | Every 5 min | No (simulation) |
| Gmail IMAP intake (in the cron) | Unread emails with allowed attachments; optional subject filter only if configured | Every 5 min | n/a |

- Ignored blob prefixes: `archive/ processed/ failed/ error-reports/ .`
- Email context (`sender_email`, `email_subject`, `body_fields`, `requisition_id`)
  is read from **blob metadata** set by the intake layer (Gmail/manual upload or
  whichever intake writes the blob metadata).
- A processed-blob guard (`fact_processed_blobs`) stops double-processing; the
  instant Function App trigger normally wins, the cron is a backstop.

---

## 2. Two parallel "email" systems

1. **Live ACS** — `onboarding_pipeline.py` + `document_pipeline.py` →
   `email_service.py` → Azure Communication Services. Gated by
   `EMAIL_SIMULATION_MODE` only. **These actually send.**
2. **Prepared queue + live ACS best-effort** — `pipeline_service.py` writes
   `fact_communications` rows and then attempts to send the prepared communication
   through ACS when `EMAIL_SIMULATION_MODE=false`. Baja, correction, HR package,
   Coparmex package, and file processed communications use this path.

---

## 3. Live onboarding emails (the ~12-step flow)

From `practicantes@…azurecomm.net`.

| # | Fires when | To | Subject | Body gist | Attach |
|---|---|---|---|---|---|
| 1 | Requisición `.docx` OK | requester (`sender_email`) | `Requisición recibida – ID de posición REQ-2026-NNNN` | Position ID; add it to new-hires list or email body | — |
| 1b | Requisición/alta fails | sender | `Devolución: …` | What to fix & resend | — |
| 2 | HR new-hires list processed → **Paquete 1** | new hire (personal) | `¡Te damos la bienvenida a Cemex! Paquete 1 – Summer Internship Program` | Requests data + 6 docs | alta template |
| 3 | Paquete 1 complete & valid | candidate | `Documentos recibidos – Summer Internship Program` | Confirms; convenio copy + NDA coming | — |
| 3b | Docs incomplete | sender/candidate | `Devolución: documentos del practicante (Paquete 1)` | Missing/problem list | — |
| 4 | HR convenio+NDA in & P1 done → **Welcome 2** | candidate | `¡Te damos la bienvenida a Cemex! Documentos – Summer Internship Program` | Convenio is copy-only; sign NDA DOCX and return PDF as `Nombre_Apellido_NDA.pdf` | convenio+NDA |
| 5 | Candidate returns signed NDA PDF | HR | `NDA firmado recibido` | Signed NDA complete → attach PDF to HR → finalize | NDA PDF |
| 6 | Finalize (always) | practicante | `Gracias – Summer Internship Program` | Thanks; will follow up | — |
| 7a | Finalize, data complete | RH | `FAVOR DE GESTIONAR CONVENIO (RH reenviar a Coparmex) – {nombre}` | Coparmex-ready fields for RH review/forward | alta format ⚠️ |
| 7b | Finalize, complete | HR | `Practicante dado de alta exitosamente` | Success + Power BI link | — |
| 7c | Finalize, unresolved data missing | HR | `Practicante procesado – faltan datos para Coparmex ({nombre})` | Rare case: fields matching could not resolve | — |
| 7d | Current sync leaves org fields empty | HR | `Campos organizacionales por completar – {archivo}` | Excel rows for manual completion | Excel |

**Attachments**: ACS attachment sending is wired through
`email_service._build_attachments`. Unreadable attachments are skipped with a log
note instead of failing the whole email.

---

## 4. Prepared communications — `fact_communications`

`Correction needed` (→ Intern), `HR package ready` (→ HR), `Coparmex package
ready` (→ RH for review/forward), `File processed` (→ Intern), and
**`Baja De Practicante - {nombre}`** (→ HR, template `ET_BAJA`, full intern
dossier + "FAVOR DE GESTIONAR BAJA"). These are stored in `fact_communications`
and sent live best-effort through ACS when email simulation is off.

---

## 5. Recipients & resolution ⚙️

- **RH + Coparmex-ready flow (live):** `RH_RECIPIENT_EMAILS` env var; fallback
  `dim_email_recipients` table. Coparmex-ready emails are sent to RH only.
- **Person:** practicante → CEMEX email; new-hire → personal (`resolve_person_email`).
- **Baja/prepared:** `RH_RECIPIENT_EMAILS` through `resolve_group_recipients`,
  with legacy table fallback.

---

## 6. Packages & documents

- **Paquete 1 required** (`REQUIRED_CANDIDATE_DOCS`): `alta, curp, constancia,
  identificacion, comprobante_domicilio, acta`. `foto` optional/removed. ⚙️
- **Convenio round:** HR uploads convenio + NDA. Convenio is copy-only for the
  candidate. NDA must be sent as DOCX and returned signed as PDF; only signed NDA
  is required to complete this round.
- **Coparmex fields:** nombre, F. nacimiento, correo personal, universidad,
  carrera, semestre, F. graduación, CEMEX-ID, correo institucional, VP, proyecto,
  jefe directo, AIRH, UDN, compañía, OI, CC, sueldo real desde `salario_mensual`,
  F. ingreso/fin, estado. Blocks send if any of
  `cemex_id, correo_institucional, ubicacion_udn, compania, ubicacion_estado, oi, cc`
  is missing.

---

## 7. Validations & matching

- **Candidate (alta):** R009 nombre, R010 email format, CURP 18-char regex,
  R003 carrera, birthdate not future; warning if carrera ≠ requisición.
- **Documents:** filename + content keyword classification; identity check (name
  must appear in doc/filename); CURP cross-checked vs alta; graduation pulled from
  constancia; signed NDA must be a PDF and follow the signed-file naming convention.
- **OCR:** Azure Document Intelligence `prebuilt-read` `api-version=2023-07-31`,
  only for scanned PDFs (<30 chars text) / images.
- **Matching:** Position ID → personal email → full name; org enrichment via W1
  `dim_manager_assignments` keyed by jefe directo.

---

## 8. Codes, tags, IDs (keys)

- **Status:** `ST002` active; `ST003`/`ST004` inactive/baja.
- **Process types:** `PROC_NEW_HIRE, PROC_REQUISITION, PROC_CURRENT_SYNC,
  PROC_BAJA, PROC_ALTA, PROC_DOCUMENT_REFRESH`; requisition type `PT006`.
- **Email matching:** metadata/body fields, attachment names/content, sender email,
  and `REQ-{year}-{0000}` when present. Subject tags are optional, not required.
- **ID formats:** `REQ-{year}-{0000}`, `PRA-{year}-{0000}`, `BEN-{uuid8}`,
  `DOC-{uuid8}`; template id `ET_BAJA`.

---

## 9. Config knobs (env) ⚙️

`EMAIL_SIMULATION_MODE`, `ACS_SENDER_EMAIL`, `ACS_SENDER_NAME`,
`ACS_CONNECTION_STRING`, `RH_RECIPIENT_EMAILS`, `POWERBI_DASHBOARD_URL`,
`DOC_INTEL_ENDPOINT/KEY`,
`DEV_EMAIL_OVERRIDE`. Inert legacy: `EMAIL_MODE`, `SEND_EMAILS`.

---

## 10. Open decisions ⚠️

1. **Sender `@azurecomm.net`** (spam-prone); `cemex.com` exists but DNS-unverified.
2. **Full cost sync** — re-upload W1 roster with real `Importe` / `ImporteTotal`.
3. **Open positions process tracking** — decide if `dim_open_positions` uploads
   should create formal `PROC_POSITIONS_SYNC` runs.
4. **Scheduled RH digest** — optional weekly/monthly email for expired active
   contracts and pending actions.
