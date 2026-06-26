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
- Email (ACS): resource `intern-pipeline-comm-dev`, email service `intern-pipeline-email-dev`.
  - AzureManagedDomain `cca4d0a7-2ca3-4728-a5cd-5dab25a27ac4.azurecomm.net` (verified).
  - Custom domain `cemex.com` exists but is **DNS-unverified** (no DNS access).
  - Sender: **`practicantes@…azurecomm.net`** ("Programa de Practicantes CEMEX").

**Email behavior (live)**
- `email_service.py` (ACS) is the single sender; gated by `EMAIL_SIMULATION_MODE`.
  On the live app it is **`false` (real sends ON)**. Attachments are supported.
- Recipients: `RH_RECIPIENT_EMAILS` / `COPARMEX_RECIPIENT_EMAILS` env vars are the
  single source of truth (both `pipeline_service.resolve_group_recipients` and
  onboarding use them). Currently both = `bryan.gomez@ext.cemex.com` (testing).
- Coparmex emails now go to **RH** (they forward to Coparmex).
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
- Never print/commit secrets (`.env`, connection strings, ACS/SQL keys). `.env` and
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
- **Custom email domain**: verify `cemex.com` in ACS (needs DNS records) to send from a
  `@cemex.com` address and improve deliverability. Needs DNS access Bryan doesn't have.
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
