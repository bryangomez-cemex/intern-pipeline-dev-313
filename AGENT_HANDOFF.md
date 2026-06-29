# Agent Handoff

Shared log between AI agents (Claude, Codex, …) working on this repo. **Read this
first** when you start, and **append an entry** to the Session Log when you finish.
Keep "Key facts" and "Open ideas / TODO" current; don't let them go stale.

Owner: Bryan (bryan.gomez@ext.cemex.com). Production system: CEMEX intern pipeline.

---

## Key facts (keep current)

**Azure (CEMEX subscription `a3d54e37-bfef-4efb-8f09-f6d848b499c7`, tenant `6ee19001-…`)**
- Resource group: `rg-intern-pipeline-dev`
- Function App: `mex-intern-pipeline-func-win` — **Flex Consumption**, Linux, Python 3.11.
  - Deploy: `az functionapp deployment source config-zip -g rg-intern-pipeline-dev -n mex-intern-pipeline-func-win --src pkg.zip --build-remote true` (remote Oryx build; ship source only). Classic Kudu `/api/zipdeploy` does NOT work on Flex.
  - CI workflow `.github/workflows/deploy-mex-function.yml` uses `Azure/functions-action@v2` + `remote-build: true`, triggers on push to `main`.
- SQL: server `rg-intern-system-devbge.database.windows.net`, db `rg-intern-system-dev`.
  - Firewall: Bryan's IP changes (mobile). Add a temp single-IP rule when local SQL access is blocked, e.g. `az sql server firewall-rule create -g rg-intern-pipeline-dev -s rg-intern-system-devbge --name claude-tmp --start-ip-address <ip> --end-ip-address <ip>`.
- Storage: `rginternpipelinedevb961` (containers raw-uploads, archive, error-reports).
- Document Intelligence: `docintel-intern-pipeline-dev` (`DOC_INTEL_ENDPOINT`/`DOC_INTEL_KEY`).
- Email send/receive now uses Gmail app credentials.
  - Inbound: Azure Function timer `gmail_intake_timer` reads Gmail IMAP
    (`IMAP_USERNAME` / `IMAP_PASSWORD`) every 5 minutes.
  - Outbound: Function App Gmail SMTP (`SMTP_USERNAME` / `SMTP_PASSWORD`).
  - ACS email resources may still exist in Azure but are no longer the active
    application email path.

**Email behavior (live)**
- `email_service.py` (Gmail SMTP) is the single sender; gated by `EMAIL_SIMULATION_MODE`.
  On the live app it is **`false` (real sends ON)**. Attachments are supported.
- Recipients: `RH_RECIPIENT_EMAILS` is the single source of truth for RH and
  Coparmex-ready emails. Currently = `bryan.gomez@ext.cemex.com` (testing).
- Coparmex-ready emails go to **RH only**; RH reviews quickly and forwards to
  Coparmex manually.
- Baja + the four prepared comms (Correction / HR package / Coparmex / File processed)
  now send live (best-effort, marked Sent).

**Code layout**
- Source of truth: `scripts/`. The Function App copies live in `azure_function_app/scripts/`
  and must be kept in sync (the deploy rsyncs `scripts/` → there). After editing a
  module under `scripts/`, `cp` it to `azure_function_app/scripts/` (or run the deploy,
  which rsyncs).
- SQL: `scripts/sql/`. Power BI views: `create_business_powerbi_views.sql`,
  `2026-06_powerbi_no_dax_views.sql`, `2026-06_powerbi_refinements.sql`. Apply by
  splitting on `GO` and executing via `azure_clients.get_sql_connection()`.

**Conventions**
- Never print/commit secrets (`.env`, connection strings, Gmail app passwords,
  SQL keys). `.env` and
  `EXAMPLES/` are gitignored. `ROTATE_SECRETS.md` tracks exposed creds Bryan must rotate.
- Power BI: only the VALUES need to be in Spanish (column/table names can stay English).
- Production deploys + pushes to `main` need Bryan's explicit go-ahead (safety guard).

---

## Open ideas / TODO

- **Re-upload the full roster** (W1-PRACTICANTES with all 302 + amount columns) so
  `importe` (pay) and `importe_total` (company cost) populate exactly for everyone.
  This session added the cost columns/views and backfilled the rows in the local
  sample; the rest use a `salario_mensual x 1.1` (comision factor) approximation until
  re-synced. Cost model: `Importe`=`ImporteSinComision`=intern pay; `ImporteTotal`=
  total company cost.
- **CI deploy on `main` fails** (`Azure/functions-action` + publish-profile on this Flex
  app — 5s failure; couldn't read Actions logs to confirm cause). Deploys are done via
  `az ... config-zip --build-remote` (works). To fix CI properly, configure OIDC
  (`azure/login`) + `az functionapp deployment`, which needs a service principal /
  federated credential (app registration may be restricted in the CEMEX tenant).
- **Gmail app password**: rotate if it is exposed, keep it only in Azure Function
  App settings, and avoid committing it to docs or `.env`.
- **Open positions → process type**: `dim_open_positions` snapshot is a separate path,
  not tied to the `PROC_*` intern lifecycle process types. Add `PROC_POSITIONS_SYNC`
  if position uploads should be tracked in `fact_pipeline_runs` like other processes.
- **Scheduled self-check digest**: the system already flags inactivos / expired /
  expiring live via the Power BI views and detects bajas on sync (now emailing RH).
  `scripts/send_expired_active_contracts_email.py` exists for a one-off report; a
  scheduled (e.g. weekly) digest email to RH could be wired if wanted.
- (done) `POWERBI_DASHBOARD_URL` set to the real report; onboarding emails render a
  clickable "PowerBI - Practicantes" hyperlink (via the `{{POWERBI_LINK}}` token).
- Consider resolving `fact_intern_missing_items` BusinessRule rows in the pipeline when
  matching fills the field (today they stay Open and are only reframed as "Resuelta" in
  the exceptions view).

---

## Session log (newest first)

### 2026-06-29 — Claude (Opus 4.8)
- Ran a full **online** end-to-end test (uploaded fake `ZZZTEST` files to `raw-uploads`,
  let the live `gmail_intake_timer` process them, verified in Azure SQL). All fake data
  was deleted afterward (DB rows + blobs); baselines back to 302/33/0.
- **Verified working online:** Gmail-timer intake/processing, classification, open-positions
  ingestion + AUTO-number, current-intern sync (importe/importe_total/razon_social),
  requisition → REQ id, Gmail SMTP sending (Intern Confirmation / Coparmex→RH / HR Package
  all `Sent`), blob archival to `archive/processed`.
- **🐞→✅ BUG FOUND & FIXED — baja email never fired (now fixed).** Across all history: `inactive_or_baja Observed`
  = 44, but `baja_requested` / `Baja De Practicante` communications = **0**. Cause:
  `prepare_baja_communication` is gated by `is_active_to_baja_transition(previous_status,
  incoming_status)` where `previous_status = get_effective_intern_status(...)`, which reads
  the LATEST `fact_intern_lifecycle_events.new_status`. The `inactive_or_baja Observed`
  alert (new_status=Inactivo) is recorded for the same row, so `previous_status` already
  reads `Inactivo` → transition is `inactive→inactive` → False → baja email is never
  prepared/sent. Detection (status flip, Power BI inactivos) works; only the RH baja
  notification was missing. **FIXED (commit `b20717f`, deployed + verified online):**
  `previous_status` now reads `dim_interns.status_id` (the persisted value) before the
  upsert, instead of `get_effective_intern_status` (which read lifecycle events). Verified
  online: a fresh active intern marked inactive produced a `Baja De Practicante` **Sent**
  communication + a `baja_requested` event.
- Validation note: a roster row with an inactive status needs `Universidad` or it fails
  validation ("Missing university"); active rows pass without it.

### 2026-06-29 — Codex
- Adjusted existing Power BI open-positions view only; no new Power BI table/view
  was created.
- `vw_powerbi_posiciones_abiertas.id_vacante` now returns the real `ID Vacante`
  when present, otherwise `AUTO-{numero}` using the generated unique position
  number.
- Applied live SQL and verified:
  - `vw_powerbi_posiciones_abiertas`: 33 current rows.
  - `blank_vacante_id`: 0.
  - Missing source IDs now show values such as `AUTO-900030`.

### 2026-06-29 — Codex
- Added automatic open-position number generation.
  - Runtime creates/uses SQL sequence `dbo.seq_open_position_num`.
  - If an uploaded open position has empty `#` / `numero`, or duplicates a number
    already seen in that upload, the system assigns a generated unique number.
  - Generated numbers use the `900000+` range to avoid confusion with human-entered
    file values.
  - Applied live SQL backfill: current `dim_open_positions` now has 33 current rows,
    0 missing numbers, and 33 distinct numbers.
- Added Gmail `Menu` request support.
  - If an unread email contains `Menu` / `menu` / `menú` in subject or body, the
    intake replies with supported system actions and marks the email as read.
  - Menu reply lists: open positions, current roster sync, new hires, requisition,
    Paquete 1, convenio/NDA.
- Updated behavior/technical docs and Function App copies.
- Validated with `py_compile`, `check_function_readiness`, `smoke_e2e_pipeline`,
  menu detector assertions, and `git diff --check`.

### 2026-06-29 — Codex
- Investigated Bryan's positions email not showing in Power BI.
- Found Gmail intake worked: the attachment landed in `raw-uploads` as
  `email_intake/20260629_191001_uid_7_data_(2).xlsx`.
- Found the storage account currently has no Event Grid subscription, so
  `process_raw_upload` was indexed but not being triggered automatically for the
  new blob.
- Updated `gmail_intake_timer` so every 5 minutes it now:
  1. reads unread Gmail attachments into `raw-uploads`;
  2. lists pending blobs in `raw-uploads`;
  3. calls `process_blob_by_name(...)` for each pending blob, up to
     `GMAIL_INTAKE_MAX_PENDING_BLOBS` (default 25).
- This makes Gmail/email uploads self-contained even when Event Grid is missing.
- Deployed this fix to Azure Function App.
  - Deployment id: `ee0424a8-f984-447c-8fe6-d650bc7d033a`.
  - Verified functions indexed: `gmail_intake_timer`, `process_raw_upload`,
    `setup_database`, `setup_database_on_startup`.
- Verified the stuck positions upload was processed:
  - Raw blob `email_intake/20260629_191001_uid_7_data_(2).xlsx` moved to
    `archive/processed/...` at `2026-06-29T19:30:04Z`.
  - `dim_open_positions`: 33 current rows.
  - `vw_powerbi_posiciones_abiertas`: 33 rows.

### 2026-06-29 — Codex
- Switched active email path away from Azure Communication Services.
- `scripts/email_service.py` now sends through Gmail SMTP using
  `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_EMAIL`; Function App copy synced.
- Added Azure Function timer `gmail_intake_timer` (every 5 minutes) so Azure reads
  Gmail IMAP directly and uploads allowed attachments to `raw-uploads`.
- Moved Gmail intake module into `azure_function_app/scripts/` and changed its
  download temp folder to `/tmp/email_intake_downloads` for Azure Functions.
- Changed `.github/workflows/mvp-ingestion.yml` to manual blob-ingestion only; it
  no longer schedules Gmail intake or references IMAP secrets.
- Configured live Function App app settings for Gmail IMAP/SMTP and removed
  `ACS_CONNECTION_STRING`, `ACS_SENDER_EMAIL`, and `ACS_SENDER_NAME`.
- Removed obsolete GitHub Secrets `IMAP_USERNAME` and `IMAP_PASSWORD` because
  GitHub no longer owns Gmail intake.
- Added `ROTATE_SECRETS.md` note for the Gmail app password because it was shared
  during setup; rotate after confirming the new path works.
- Validated with `py_compile`, `.venv/bin/python scripts/check_function_readiness.py`,
  `.venv/bin/python scripts/smoke_e2e_pipeline.py`, and `git diff --check`.

### 2026-06-29 — Claude (Opus 4.8)
- Added **costos por compania**: `razon_social_hc` on `dim_interns` (RAZON SOCIAL HC =
  legal company name, distinct from CIA HC code) wired into the current-intern MERGE;
  new `vw_powerbi_costos_por_compania` (importe_total = company cost, importe = pay, by
  company). Applied live; backfilled the local roster sample (rest = "Sin compania"
  until full roster re-sync).
- **⚠️ Caused + fixed a regression**: while two agents were on this repo, my checkout
  switched to local `main` (which is BEHIND `codex` — missing Codex's routing/NDA/acta
  work). A deploy from that state briefly reverted Codex's work on the live app. Fixed:
  re-applied the costos change on top of `codex` and redeployed (id `61ecb7f8`), verified
  the package has BOTH Codex's work (routing, acta) AND costos. `origin/codex` (`6a459aa`)
  is now the canonical, deployed source of truth.
- **Lesson**: only one agent should edit/checkout this repo at a time. `origin/main`
  (`6311e87`) is still behind `codex` — reconcile codex→main when Bryan is ready.
  (My earlier main-based costos commits live on `origin/claude/costos-por-compania`,
  now superseded by the codex re-apply — that branch can be deleted.)

### 2026-06-29 — Codex
- Bryan re-authenticated GitHub CLI locally; `gh auth status` now passes for
  `bryangomez-cemex`.
- Ran `gh auth setup-git` so Git HTTPS pushes use the authenticated GitHub CLI
  credentials.
- Pushed the previously blocked commits to GitHub branch
  `codex/intern-pipeline-production-readiness` (`b1c4805..21cf6e9`).
- Azure deploy was already completed in the prior session and was not changed in
  this step.
- Still open: merge/push to `main` if Bryan wants the GitHub scheduled intake to
  run from the updated workflow, then re-send or re-mark unread the positions
  Excel email and verify `dim_open_positions`.

### 2026-06-26 — Codex
- Updated routing and fallback behavior per Bryan's RH process notes.
- Coparmex-ready emails now route to RH only via `RH_RECIPIENT_EMAILS`; RH reviews
  quickly and forwards to Coparmex manually. Removed active use of
  `COPARMEX_RECIPIENT_EMAILS` from onboarding/pipeline routing.
- Changed onboarding/finalization copy so success says Coparmex management is
  prepared for RH review/forward, not sent directly to Coparmex.
- Changed Gmail intake default so it does not require `[INTERN]` in the subject.
  It processes unread emails with allowed attachments and uses metadata, body
  fields, filenames/content, sender, and requisition IDs when present.
- Added an RH-only Excel report for unresolved org fields after matching:
  `Campos organizacionales por completar - {source_file}` with rows/columns for
  VP HC, CC HC, OI HC, CIA HC, JefeInmediato, identifiers, location, position,
  requisition and source file. The report is sent best-effort with an attachment.
- Adjusted correction communication behavior so non-blocking warning rows do not
  trigger the generic "Correccion requerida" email by themselves.
- Updated README, technical manual, RH manual, behavior reference, workflow env,
  and Function App copies via `scripts/sync_function_modules.py`.

### 2026-06-26 — Codex
- Applied and deployed the latest onboarding/intake changes.
- Azure SQL live:
  - Re-applied `scripts/sql/2026-06_package1_document_requirements.sql`.
  - Verified `RDT_ACTA_NACIMIENTO` is required for `PROC_ALTA` and `PROC_NEW_HIRE`.
- Investigated Bryan's email with the positions Excel:
  - `raw-uploads` had no recent blobs.
  - `archive` only showed older `Layout_junio_2026.xlsx` rows and the Coparmex template.
  - `dim_open_positions` had `0` rows and no `updated_at`.
  - Most likely cause: the old Gmail intake required subject tag `[INTERN]`, so the email
    was not picked up before reaching Blob/Function. This session changed the default
    intake to process unread emails with allowed attachments without requiring a fixed
    subject tag.
- Deployed local source package from commit `f1a6f70` to Azure Function App
  `mex-intern-pipeline-func-win`.
  - Deployment id: `9f4a11cb-44a9-447b-9dd6-564699e0a425`.
  - Azure result: `Deployment was successful.`
  - Verified resource state `Running`, indexed functions `process_raw_upload`,
    `setup_database`, `setup_database_on_startup`.
  - Verified non-secret email settings: `EMAIL_SIMULATION_MODE=false`,
    `RH_RECIPIENT_EMAILS=bryan.gomez@ext.cemex.com`, sender `practicantes@...azurecomm.net`.
- GitHub push is currently blocked locally:
  - `git push` failed with `could not read Username for 'https://github.com'`.
  - `gh auth status` reports the GitHub token for `bryangomez-cemex` is invalid.
  - Local commits exist and need to be pushed after re-authentication.

### 2026-06-26 — Codex
- Updated convenio/NDA behavior in code and docs.
- The convenio is now treated as copy-only for the candidate; it is no longer part
  of the required signed return set.
- The NDA original from HR must be DOCX; non-DOCX NDA originals are stored as
  `problem`, return a correction email to the sender, and do not trigger the
  candidate send.
- The candidate only needs to return the signed NDA as PDF. A non-PDF signed NDA
  is stored as `problem`, returns a correction email to the sender, and does not
  complete the round.
- When the signed NDA PDF is received, the system marks the round complete, sends
  `NDA firmado recibido` to RH with the signed PDF attached, then finalizes
  onboarding.
- Updated `docs/system_behavior_reference.md`, `docs/technical_manual.md`, and
  `docs/hr_manual.md` to match.

### 2026-06-26 — Codex
- Made `Acta de nacimiento` a required Paquete 1 document.
- Updated hardcoded package validation in `scripts/document_pipeline.py` and the
  Function App copy, adding `acta` to `REQUIRED_CANDIDATE_DOCS` and content
  keywords.
- Updated `2026-06_package1_document_requirements.sql` in both SQL locations so
  `RDT_ACTA_NACIMIENTO` is active/required for `PROC_NEW_HIRE` and `PROC_ALTA`,
  and no longer gets resolved as a legacy optional missing item.
- Updated RH/technical docs, behavior reference, and alert recommendations to say
  Paquete 1 now requires 6 documents including acta.

### 2026-06-26 — Codex
- Updated documentation only; no deploy performed.
- Replaced `docs/technical_manual.md` with a Spanish technical manual covering
  architecture, stack, Azure resources, Function App behavior, SQL setup order,
  Blob contract, email/ACS behavior, baja flow, matching rules, Power BI views,
  operations, monitoring, security, costs, and known open items.
- Added `docs/hr_manual.md`, a Spanish RH-facing operating manual covering file
  types, onboarding, Paquete 1, convenio/NDA, bajas, contracts, missing documents,
  org-field matching, Power BI usage, processing expectations, and escalation info.
- Refreshed `docs/system_behavior_reference.md` so it reflects the current live
  sender (`practicantes@...azurecomm.net`), prepared communications live-send
  behavior, env-var recipient resolution, real salary source for Coparmex, wired
  ACS attachments, and the current open decisions.

### 2026-06-26 — Codex
- Pushed the production-readiness follow-up fixes to GitHub `main`.
  - `main` moved from `60ce411` to `6bab18e` (`Merge production readiness follow-up fixes`).
  - The merge brought in `74c79ef` and `f71684c`.
- Published the merged `main` source package to the live Azure Function App
  `mex-intern-pipeline-func-win` using Flex remote build.
  - Package source commit: `6bab18e`.
  - Azure deployment id: `71a21d2b-a7b3-4e8d-a840-50954d7706b6`.
  - Azure result: `Deployment was successful.`
- Verified after publish:
  - Function App state: `Running`.
  - Indexed functions: `process_raw_upload`, `setup_database`, `setup_database_on_startup`.
  - Live email settings still show real sends on to Bryan for testing:
    `EMAIL_SIMULATION_MODE=false`, `RH_RECIPIENT_EMAILS=bryan.gomez@ext.cemex.com`,
    `COPARMEX_RECIPIENT_EMAILS=bryan.gomez@ext.cemex.com` (historical; current
    code routes Coparmex-ready emails through `RH_RECIPIENT_EMAILS` only).
- Left existing local changes untouched:
  - `docs/system_behavior_reference.md`
  - `NA FORMATO PARA ALTA DE PRACTICANTE COPARMEX.xlsx`

### 2026-06-26 — Claude (Opus 4.8)
Big batch of changes (all committed; SQL views applied live; code deployed):
- **Power BI** (`2026-06_powerbi_refinements.sql`, applied live): `capacity_status` is a
  numeric percentage; `risk_bucket` de-enumerated + Spanish, inactivos → "Realizar baja";
  exceptions carry `estado` (Resuelta automaticamente vs Pendiente — empty fields filled
  by matching report as resolved), graduated Spanish severities (Critica/Alta/Media/Baja),
  short useful Spanish suggestions; KPIs split pendientes (63) vs resueltas (102); HR queue
  categories/severities in Spanish.
- **Email**: wired Correction / HR package / Coparmex / File processed to send live;
  Coparmex → RH; unified recipients to the env vars; Spanish bodies.
- **Salary**: Coparmex "Sueldo" uses real `salario_mensual` (not `$8800`); `ImporteTotal`
  no longer aliased to salary.
- **Open positions** ingestion: `dim_open_positions` + `vw_powerbi_posiciones_abiertas`,
  classifier + `process_open_positions`, routed. (lista de posiciones abiertas)
- **Documents**: owner identified by content (CURP), name no longer required in the file.
- **ACS sender**: new username `practicantes@…azurecomm.net` ("Programa de Practicantes
  CEMEX"); app `ACS_SENDER_EMAIL` updated.
- Earlier same day: ACS email service + attachments, baja live-send, system behavior
  reference (`docs/system_behavior_reference.md`), Flex deploy fix. See git log + PR #1.
- Follow-up tweaks (same day): cost columns `importe`/`importe_total` (real ImporteTotal
  = company cost, Importe = intern pay) + view + backfill; Coparmex template uploaded to
  `archive/templates/alta_coparmex.xlsx`; Power BI hyperlink + `POWERBI_DASHBOARD_URL`
  set; sender `practicantes@` confirmed. **PR #1 merged to `main`** — the app is live via
  `az`; the CI publish-profile deploy on `main` fails (see Open ideas).

### (template for the next agent)
### YYYY-MM-DD — <Agent>
- What changed / decided / why. What's deployed. What's still open.
