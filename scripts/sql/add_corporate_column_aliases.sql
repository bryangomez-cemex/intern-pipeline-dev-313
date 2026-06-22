/* Corporate CEMEX column aliases.
   Safe to rerun. Does not drop tables or data.

   Run after scripts/sql/create_full_mvp_pipeline.sql so dim_canonical_fields
   and dim_column_aliases exist.
*/

IF OBJECT_ID('dbo.dim_canonical_fields', 'U') IS NULL
BEGIN
    RAISERROR('dbo.dim_canonical_fields does not exist. Run create_full_mvp_pipeline.sql first.', 16, 1);
END;
GO

IF OBJECT_ID('dbo.dim_column_aliases', 'U') IS NULL
BEGIN
    RAISERROR('dbo.dim_column_aliases does not exist. Run create_full_mvp_pipeline.sql first.', 16, 1);
END;
GO

MERGE dbo.dim_canonical_fields AS target
USING (VALUES
    ('position_code', 'position_code', 'Corporate position code.'),
    ('job_code', 'job_code', 'Corporate job code.'),
    ('location', 'location', 'Corporate work location.'),
    ('location_state', 'location_state', 'Corporate work location state.'),
    ('manager_number', 'manager_number', 'Manager employee number.'),
    ('manager_code', 'manager_code', 'Manager corporate code.'),
    ('personnel_lead', 'personnel_lead', 'Personnel or HR advisor.'),
    ('company_code', 'company_code', 'Company code.'),
    ('payment_frequency', 'payment_frequency', 'Payment frequency.'),
    ('user_id', 'user_id', 'Corporate user id.'),
    ('sap_user_id', 'sap_user_id', 'SAP user id.')
) AS source (canonical_field_id, canonical_field_name, description)
ON target.canonical_field_id = source.canonical_field_id
WHEN NOT MATCHED THEN
    INSERT (canonical_field_id, canonical_field_name, description)
    VALUES (source.canonical_field_id, source.canonical_field_name, source.description);
GO

MERGE dbo.dim_column_aliases AS target
USING (VALUES
    ('alias_corp_numero', 'employee_number', 'NUMERO', 'numero', 'corporate'),
    ('alias_corp_nombre', 'full_name', 'NOMBRE', 'nombre', 'corporate'),
    ('alias_corp_codpos', 'position_code', 'CODPOS', 'codpos', 'corporate'),
    ('alias_corp_cvepto', 'job_code', 'CVEPTO', 'cvepto', 'corporate'),
    ('alias_corp_descripcionpuesto', 'position', 'DESCRIPCIONPUESTO', 'descripcionpuesto', 'corporate'),
    ('alias_corp_vicepresidencia', 'vp_hc', 'VICEPRESIDENCIA', 'vicepresidencia', 'corporate'),
    ('alias_corp_regionarea', 'area', 'REGIONAREA', 'regionarea', 'corporate'),
    ('alias_corp_gerencia', 'area', 'GERENCIA', 'gerencia', 'corporate'),
    ('alias_corp_gerencianombre', 'manager', 'GERENCIANOMBRE', 'gerencianombre', 'corporate'),
    ('alias_corp_gerentenombre', 'manager', 'GERENTENOMBRE', 'gerentenombre', 'corporate'),
    ('alias_corp_ubicacion', 'location', 'UBICACION', 'ubicacion', 'corporate'),
    ('alias_corp_edoubicacion', 'location_state', 'EDOUBICACION', 'edoubicacion', 'corporate'),
    ('alias_corp_jefedepersonal', 'personnel_lead', 'JEFEDEPERSONAL', 'jefedepersonal', 'corporate'),
    ('alias_corp_numerojefe', 'manager_number', 'NUMEROJEFE', 'numerojefe', 'corporate'),
    ('alias_corp_nombrejefe', 'manager', 'NOMBREJEFE', 'nombrejefe', 'corporate'),
    ('alias_corp_codjefe', 'manager_code', 'CODJEFE', 'codjefe', 'corporate'),
    ('alias_corp_cia', 'company_code', 'CIA', 'cia', 'corporate'),
    ('alias_corp_ciastr', 'company', 'CIASTR', 'ciastr', 'corporate'),
    ('alias_corp_cc', 'cc_hc', 'CC', 'cc', 'corporate'),
    ('alias_corp_ordeninterna', 'oi_hc', 'ORDENINTERNA', 'ordeninterna', 'corporate'),
    ('alias_corp_ccoperativo', 'cc_hc', 'CCOPERATIVO', 'ccoperativo', 'corporate'),
    ('alias_corp_email', 'email', 'EMAIL', 'email', 'corporate'),
    ('alias_corp_userid', 'user_id', 'USERID', 'userid', 'corporate'),
    ('alias_corp_useridsap', 'sap_user_id', 'USERIDSAP', 'useridsap', 'corporate'),
    ('alias_intern_numempleado', 'employee_number', 'NumEmpleado', 'numempleado', 'intern_template'),
    ('alias_intern_numempleadocemex', 'cemex_employee_number', 'NumEmpleadoCemex', 'numempleadocemex', 'intern_template'),
    ('alias_intern_nss', 'nss', 'NSS', 'nss', 'intern_template'),
    ('alias_intern_rfc', 'rfc', 'RFC', 'rfc', 'intern_template'),
    ('alias_intern_curp', 'curp', 'CURP', 'curp', 'intern_template'),
    ('alias_intern_nombre', 'first_name', 'Nombre', 'nombre', 'intern_template'),
    ('alias_intern_paterno', 'paternal_last_name', 'Paterno', 'paterno', 'intern_template'),
    ('alias_intern_materno', 'maternal_last_name', 'Materno', 'materno', 'intern_template'),
    ('alias_intern_nombrecompleto', 'full_name', 'NombreCompleto', 'nombrecompleto', 'intern_template'),
    ('alias_intern_puesto', 'position', 'Puesto', 'puesto', 'intern_template'),
    ('alias_intern_razon_social_hc', 'company', 'RAZON SOCIAL HC', 'razon social hc', 'intern_template'),
    ('alias_intern_razonsocial', 'company', 'RazonSocial', 'razonsocial', 'intern_template'),
    ('alias_intern_fechaingreso', 'start_date', 'FechadeIngreso', 'fechadeingreso', 'intern_template'),
    ('alias_intern_fechacontratovence', 'end_date', 'FechaContratoVence', 'fechacontratovence', 'intern_template'),
    ('alias_intern_jefeinmediato', 'manager', 'JefeInmediato', 'jefeinmediato', 'intern_template'),
    ('alias_intern_ubicacion_hc', 'location', 'UBICACIÓN HC', 'ubicacion hc', 'intern_template'),
    ('alias_intern_estado_ubicacion_hc', 'location_state', 'ESTADO UBICACIÓN HC', 'estado ubicacion hc', 'intern_template'),
    ('alias_intern_asesor_rrhh_hc', 'personnel_lead', 'ASESOR RRHH HC', 'asesor rrhh hc', 'intern_template'),
    ('alias_intern_salariomensual', 'salary', 'SalarioMensual', 'salariomensual', 'intern_template'),
    ('alias_intern_cc_hc', 'cc_hc', 'CC HC', 'cc hc', 'intern_template'),
    ('alias_intern_vp_hc', 'vp_hc', 'VP HC', 'vp hc', 'intern_template'),
    ('alias_intern_regionrh', 'region_rh', 'RegionRH', 'regionrh', 'intern_template'),
    ('alias_intern_oi_hc', 'oi_hc', 'OI HC', 'oi hc', 'intern_template'),
    ('alias_intern_frecuenciapago', 'payment_frequency', 'FrecuenciaPago', 'frecuenciapago', 'intern_template'),
    ('alias_intern_importe', 'salary', 'Importe', 'importe', 'intern_template'),
    ('alias_intern_importetotal', 'salary', 'ImporteTotal', 'importetotal', 'intern_template'),
    ('alias_intern_estatus', 'status', 'Estatus', 'estatus', 'intern_template'),
    ('alias_intern_cia_hc', 'company', 'CIA HC', 'cia hc', 'intern_template')
) AS source (column_alias_id, canonical_field_id, alias_name, normalized_alias_name, source_profile)
ON target.column_alias_id = source.column_alias_id
WHEN NOT MATCHED THEN
    INSERT (column_alias_id, canonical_field_id, alias_name, normalized_alias_name, source_profile, confidence)
    VALUES (source.column_alias_id, source.canonical_field_id, source.alias_name, source.normalized_alias_name, source.source_profile, 1.0);
GO
