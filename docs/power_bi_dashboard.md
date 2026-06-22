# Power BI Dashboard

Power BI users are HR managers and VPs. Load the business views below; avoid technical file/run/blob views unless auditing a pipeline issue.

Run this SQL first:

```text
scripts/sql/create_business_powerbi_views.sql
```

## Business Views

- `vw_interns_current`
- `vw_full_mvp_interns_current`
- `vw_full_mvp_document_status`
- `vw_full_mvp_missing_items`
- `vw_full_mvp_lifecycle_events`
- `vw_business_validation_exceptions`
- `vw_requisitions_status`
- `vw_communications_status`
- `vw_hr_actions_today`

## Recommended Visuals

- Active/current interns by VP, area, manager, university, career, OI, and CC.
- Missing documents by VP, area, manager, intern, and document code.
- Upcoming expirations using `is_expiring_soon` and `days_until_contract_end`.
- Lifecycle events by process type: altas, extendimientos, bajas, current sync, document refresh.
- Business exceptions by VP, area, manager, OI, CC, company, field, severity, and next action.
- Pending requisitions by VP, area, manager, status, OI, and CC.
- Communications/actions needed by recipient group and communication status.
- HR action queue from `vw_hr_actions_today`.

## Business Questions

- How many active interns do we have?
- Who is missing documents?
- Who is expiring soon?
- Which requisitions are pending?
- Which interns have OI/CC/manager/company/date/salary issues?
- Which VP or area has the most blocked cases?
- What actions does HR need to take today?

## Verification Queries

```sql
SELECT TOP 25 * FROM dbo.vw_interns_current ORDER BY intern_name;
SELECT TOP 25 * FROM dbo.vw_full_mvp_missing_items ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_full_mvp_document_status ORDER BY intern_name, document_code;
SELECT TOP 25 * FROM dbo.vw_full_mvp_lifecycle_events ORDER BY event_date DESC;
SELECT TOP 25 * FROM dbo.vw_business_validation_exceptions ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_requisitions_status ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_communications_status ORDER BY created_at DESC;
SELECT TOP 25 * FROM dbo.vw_hr_actions_today ORDER BY action_created_at DESC;
```
