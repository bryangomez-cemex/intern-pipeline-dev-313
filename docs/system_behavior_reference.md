# Intern System – Behavior Reference

A complete map of what the system sends, receives, validates, and decides — so it
can be reviewed and adjusted. Use the **⚙️ knob** (config you can change) and
**⚠️ decision/gap** markers to drive changes.

Last reviewed: 2026-06-26. Current email state on the live Function App:
`EMAIL_SIMULATION_MODE=false` (real sends), `RH_RECIPIENT_EMAILS` and
`COPARMEX_RECIPIENT_EMAILS` = `bryan.gomez@ext.cemex.com`, sender
`DoNotReply@cca4d0a7-…azurecomm.net`.

---

## 1. How files get in (triggers & timing)

| Path | Trigger | Timing | Real email? |
|---|---|---|---|
| Function App `process_raw_upload` | Event Grid on blob create in `raw-uploads/` | Near-instant | **Yes** |
| GitHub cron `mvp-ingestion.yml` | `*/5 * * * *` | Every 5 min | No (simulation) |
| Gmail IMAP intake (in the cron) | Messages tagged `[INTERN]` → attachments to blob | Every 5 min | n/a |

- Ignored blob prefixes: `archive/ processed/ failed/ error-reports/ .`
- Email context (`sender_email`, `email_subject`, `body_fields`, `requisition_id`)
  is read from **blob metadata** set by the intake layer (Power Automate / Gmail).
- A processed-blob guard (`fact_processed_blobs`) stops double-processing; the
  instant Function App trigger normally wins, the cron is a backstop.

---

## 2. Two parallel "email" systems

1. **Live ACS** — `onboarding_pipeline.py` + `document_pipeline.py` →
   `email_service.py` → Azure Communication Services. Gated by
   `EMAIL_SIMULATION_MODE` only. **These actually send.**
2. **Prepared queue** — `pipeline_service.py` writes `fact_communications` rows
   with `status="Prepared"`. **Never auto-sent** today (the legacy SMTP/Graph
   sender is off). The **baja** notification lives here. ⚠️

---

## 3. Live onboarding emails (the ~12-step flow)

From `DoNotReply@…azurecomm.net`.

| # | Fires when | To | Subject | Body gist | Attach |
|---|---|---|---|---|---|
| 1 | Requisición `.docx` OK | requester (`sender_email`) | `Requisición recibida – ID de posición REQ-2026-NNNN` | Position ID; add it to new-hires list / subject `[INTERN][REQ-…]` | — |
| 1b | Requisición/alta fails | sender | `Devolución: …` | What to fix & resend | — |
| 2 | HR new-hires list processed → **Paquete 1** | new hire (personal) | `¡Te damos la bienvenida a Cemex! Paquete 1 – Summer Internship Program` | Requests data + 5 docs | alta template ⚠️ |
| 3 | Paquete 1 complete & valid | candidate | `Documentos recibidos – Summer Internship Program` | Confirms; convenio coming | — |
| 3b | Docs incomplete | sender/candidate | `Devolución: documentos del practicante (Paquete 1)` | Missing/problem list | — |
| 4 | HR convenio+NDA in & P1 done → **Welcome 2** | candidate | `¡Te damos la bienvenida a Cemex! Documentos – Summer Internship Program` | Sign & return as `Nombre_Apellido_Documento.pdf` | convenio+NDA ⚠️ |
| 5 | Candidate returns both signed | HR | `Convenio firmado recibido` | Signed set complete → finalize | — |
| 6 | Finalize (always) | practicante | `Gracias – Summer Internship Program` | Thanks; will follow up | — |
| 7a | Finalize, data complete | Coparmex | `FAVOR DE GESTIONAR CONVENIO – {nombre}` | Coparmex fields + gestionar | alta format ⚠️ |
| 7b | Finalize, complete | HR | `Practicante dado de alta exitosamente` | Success + Power BI link | — |
| 7c | Finalize, data missing | HR | `Practicante procesado – faltan datos para Coparmex ({nombre})` | Missing fields; Coparmex not sent | — |

⚠️ **Attachments**: as of this writing ACS attachment sending may be newly wired
(see `email_service._build_attachments`). Before that change, attachment files
were referenced in the body but not actually sent.

---

## 4. Prepared (queued, not sent) — `fact_communications`

`Correction needed` (→ Intern), `HR package ready` (→ HR), `Coparmex package
ready` (→ Coparmex), `File processed` (→ Intern), and **`Baja De Practicante -
{nombre}`** (→ HR, template `ET_BAJA`, full intern dossier + "FAVOR DE GESTIONAR
BAJA"). ⚠️ Decide whether any of these should actually email.

---

## 5. Recipients & resolution ⚙️

- **Onboarding/Coparmex (live):** `RH_RECIPIENT_EMAILS`, `COPARMEX_RECIPIENT_EMAILS`
  env vars; fallback `dim_email_recipients` table.
- **Person:** practicante → CEMEX email; new-hire → personal (`resolve_person_email`).
- **Baja/prepared (separate source!):** `dim_recipient_groups` table via
  `resolve_group_recipients`, fallback `DEV_EMAIL_OVERRIDE`. ⚠️ Not the env var.

---

## 6. Packages & documents

- **Paquete 1 required** (`REQUIRED_CANDIDATE_DOCS`): `alta, curp, constancia,
  identificacion, comprobante_domicilio`. `acta`, `foto` optional/removed. ⚙️
- **Convenio round:** needs `convenio` + `nda` (from HR, then signed back).
- **Coparmex fields:** nombre, F. nacimiento, correo personal, universidad,
  carrera, semestre, F. graduación, CEMEX-ID, correo institucional, VP, proyecto,
  jefe directo, AIRH, UDN, compañía, OI, CC, **Sueldo `$8800` hardcoded ⚠️**,
  F. ingreso/fin, estado. Blocks send if any of
  `cemex_id, correo_institucional, ubicacion_udn, compania, ubicacion_estado, oi, cc`
  is missing.

---

## 7. Validations & matching

- **Candidate (alta):** R009 nombre, R010 email format, CURP 18-char regex,
  R003 carrera, birthdate not future; warning if carrera ≠ requisición.
- **Documents:** filename + content keyword classification; identity check (name
  must appear in doc/filename); CURP cross-checked vs alta; graduation pulled from
  constancia; signed-file naming convention.
- **OCR:** Azure Document Intelligence `prebuilt-read` `api-version=2023-07-31`,
  only for scanned PDFs (<30 chars text) / images.
- **Matching:** Position ID → personal email → full name; org enrichment via W1
  `dim_manager_assignments` keyed by jefe directo.

---

## 8. Codes, tags, IDs (keys)

- **Status:** `ST002` active; `ST003`/`ST004` inactive/baja.
- **Process types:** `PROC_NEW_HIRE, PROC_REQUISITION, PROC_CURRENT_SYNC,
  PROC_BAJA, PROC_ALTA, PROC_DOCUMENT_REFRESH`; requisition type `PT006`.
- **Subject tags:** `[INTERN]`, `[INTERN][REQ-2026-NNNN]`.
- **ID formats:** `REQ-{year}-{0000}`, `PRA-{year}-{0000}`, `BEN-{uuid8}`,
  `DOC-{uuid8}`; template id `ET_BAJA`.

---

## 9. Config knobs (env) ⚙️

`EMAIL_SIMULATION_MODE`, `ACS_SENDER_EMAIL`, `ACS_SENDER_NAME`,
`ACS_CONNECTION_STRING`, `RH_RECIPIENT_EMAILS`, `COPARMEX_RECIPIENT_EMAILS`,
`POWERBI_DASHBOARD_URL` (⚠️ placeholder), `DOC_INTEL_ENDPOINT/KEY`,
`DEV_EMAIL_OVERRIDE`. Inert legacy: `EMAIL_MODE`, `SEND_EMAILS`.

---

## 10. Open decisions ⚠️

1. **Attachments** — were not sent (TODO); being wired now.
2. **Baja / prepared emails never send** — only queued.
3. **Hardcoded `$8800`** salary in Coparmex.
4. **Sender `@azurecomm.net`** (spam-prone); `cemex.com` exists but DNS-unverified.
5. **Two recipient sources** (env vs `dim_recipient_groups`) — unify?
6. **Power BI URL placeholder** appears in real HR emails.
