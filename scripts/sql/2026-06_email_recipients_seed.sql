-- HR / COPARMEX notification recipients (idempotent).
--
-- The application PREFERS the RH_RECIPIENT_EMAILS / COPARMEX_RECIPIENT_EMAILS
-- environment variables; this table is the fallback. RH_RECIPIENT_EMAILS are
-- fixed internal recipients for HR notifications. COPARMEX currently uses a
-- placeholder until the official COPARMEX recipient is provided.

IF NOT EXISTS (SELECT 1 FROM dim_email_recipients WHERE email = 'bryan.gomez@ext.cemex.com' AND recipient_group = 'HR')
    INSERT INTO dim_email_recipients (recipient_id, recipient_group, recipient_name, email, role, active_flag)
    VALUES ('ER-RH-BGOMEZ', 'HR', 'RH - Bryan Gomez', 'bryan.gomez@ext.cemex.com', 'HR Reviewer', 1);

IF NOT EXISTS (SELECT 1 FROM dim_email_recipients WHERE email = 'valeria.acunaam@cemex.com' AND recipient_group = 'HR')
    INSERT INTO dim_email_recipients (recipient_id, recipient_group, recipient_name, email, role, active_flag)
    VALUES ('ER-RH-VACUNA', 'HR', 'RH - Valeria Acuna', 'valeria.acunaam@cemex.com', 'HR Analyst', 1);

-- Placeholder until the official COPARMEX recipient is provided.
IF NOT EXISTS (SELECT 1 FROM dim_email_recipients WHERE email = 'bryan.gomez@ext.cemex.com' AND recipient_group = 'Coparmex')
    INSERT INTO dim_email_recipients (recipient_id, recipient_group, recipient_name, email, role, active_flag)
    VALUES ('ER-COP-PLACEHOLDER', 'Coparmex', 'COPARMEX (placeholder)', 'bryan.gomez@ext.cemex.com', 'External Recipient', 1);
