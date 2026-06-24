-- Onboarding workflow schema (requisición → candidate → docs → convenio → Coparmex).
-- Idempotent: safe to run repeatedly on any environment to bring the DB up to date.

-- ── dim_requisitions: requisición content fields parsed from the .docx ────────────
IF COL_LENGTH('dim_requisitions','puesto') IS NULL ALTER TABLE dim_requisitions ADD puesto NVARCHAR(300) NULL;
IF COL_LENGTH('dim_requisitions','direccion') IS NULL ALTER TABLE dim_requisitions ADD direccion NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','region_area') IS NULL ALTER TABLE dim_requisitions ADD region_area NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','asesor_rh') IS NULL ALTER TABLE dim_requisitions ADD asesor_rh NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','manager_email') IS NULL ALTER TABLE dim_requisitions ADD manager_email NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','carrera_requerida') IS NULL ALTER TABLE dim_requisitions ADD carrera_requerida NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','semestre_requerido') IS NULL ALTER TABLE dim_requisitions ADD semestre_requerido NVARCHAR(50) NULL;
IF COL_LENGTH('dim_requisitions','disponibilidad_horario') IS NULL ALTER TABLE dim_requisitions ADD disponibilidad_horario NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','periodo_estadia') IS NULL ALTER TABLE dim_requisitions ADD periodo_estadia NVARCHAR(100) NULL;
IF COL_LENGTH('dim_requisitions','fecha_inicio_solicitada') IS NULL ALTER TABLE dim_requisitions ADD fecha_inicio_solicitada DATE NULL;
IF COL_LENGTH('dim_requisitions','fecha_termino_solicitada') IS NULL ALTER TABLE dim_requisitions ADD fecha_termino_solicitada DATE NULL;
IF COL_LENGTH('dim_requisitions','descripcion_proyecto') IS NULL ALTER TABLE dim_requisitions ADD descripcion_proyecto NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','retos') IS NULL ALTER TABLE dim_requisitions ADD retos NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','responsabilidades') IS NULL ALTER TABLE dim_requisitions ADD responsabilidades NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','entregables') IS NULL ALTER TABLE dim_requisitions ADD entregables NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','habilidades') IS NULL ALTER TABLE dim_requisitions ADD habilidades NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','modalidad') IS NULL ALTER TABLE dim_requisitions ADD modalidad NVARCHAR(50) NULL;
IF COL_LENGTH('dim_requisitions','prioridad') IS NULL ALTER TABLE dim_requisitions ADD prioridad NVARCHAR(50) NULL;
IF COL_LENGTH('dim_requisitions','convenio_requerido') IS NULL ALTER TABLE dim_requisitions ADD convenio_requerido BIT NULL;
IF COL_LENGTH('dim_requisitions','needs_review') IS NULL ALTER TABLE dim_requisitions ADD needs_review BIT NULL;
IF COL_LENGTH('dim_requisitions','parse_notes') IS NULL ALTER TABLE dim_requisitions ADD parse_notes NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_requisitions','source_container') IS NULL ALTER TABLE dim_requisitions ADD source_container NVARCHAR(200) NULL;
IF COL_LENGTH('dim_requisitions','source_blob_name') IS NULL ALTER TABLE dim_requisitions ADD source_blob_name NVARCHAR(400) NULL;
IF COL_LENGTH('dim_requisitions','source_file_id') IS NULL ALTER TABLE dim_requisitions ADD source_file_id NVARCHAR(50) NULL;

-- ── dim_interns: candidate (alta), HR-list, body, and lifecycle fields ────────────
IF COL_LENGTH('dim_interns','email_personal') IS NULL ALTER TABLE dim_interns ADD email_personal NVARCHAR(200) NULL;
IF COL_LENGTH('dim_interns','telefono') IS NULL ALTER TABLE dim_interns ADD telefono NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','estado_civil') IS NULL ALTER TABLE dim_interns ADD estado_civil NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','nacionalidad') IS NULL ALTER TABLE dim_interns ADD nacionalidad NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','matricula') IS NULL ALTER TABLE dim_interns ADD matricula NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','grado') IS NULL ALTER TABLE dim_interns ADD grado NVARCHAR(100) NULL;
IF COL_LENGTH('dim_interns','fecha_nacimiento') IS NULL ALTER TABLE dim_interns ADD fecha_nacimiento DATE NULL;
IF COL_LENGTH('dim_interns','calle') IS NULL ALTER TABLE dim_interns ADD calle NVARCHAR(200) NULL;
IF COL_LENGTH('dim_interns','numero_exterior') IS NULL ALTER TABLE dim_interns ADD numero_exterior NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','colonia') IS NULL ALTER TABLE dim_interns ADD colonia NVARCHAR(150) NULL;
IF COL_LENGTH('dim_interns','poblacion') IS NULL ALTER TABLE dim_interns ADD poblacion NVARCHAR(150) NULL;
IF COL_LENGTH('dim_interns','estado_direccion') IS NULL ALTER TABLE dim_interns ADD estado_direccion NVARCHAR(100) NULL;
IF COL_LENGTH('dim_interns','codigo_postal') IS NULL ALTER TABLE dim_interns ADD codigo_postal NVARCHAR(20) NULL;
IF COL_LENGTH('dim_interns','requisition_id') IS NULL ALTER TABLE dim_interns ADD requisition_id NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','candidate_source_blob') IS NULL ALTER TABLE dim_interns ADD candidate_source_blob NVARCHAR(400) NULL;
IF COL_LENGTH('dim_interns','candidate_needs_review') IS NULL ALTER TABLE dim_interns ADD candidate_needs_review BIT NULL;
IF COL_LENGTH('dim_interns','candidate_validation_notes') IS NULL ALTER TABLE dim_interns ADD candidate_validation_notes NVARCHAR(MAX) NULL;
IF COL_LENGTH('dim_interns','cemex_id') IS NULL ALTER TABLE dim_interns ADD cemex_id NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','correo_institucional') IS NULL ALTER TABLE dim_interns ADD correo_institucional NVARCHAR(200) NULL;
IF COL_LENGTH('dim_interns','ubicacion_udn') IS NULL ALTER TABLE dim_interns ADD ubicacion_udn NVARCHAR(150) NULL;
IF COL_LENGTH('dim_interns','compania') IS NULL ALTER TABLE dim_interns ADD compania NVARCHAR(150) NULL;
IF COL_LENGTH('dim_interns','ubicacion_estado') IS NULL ALTER TABLE dim_interns ADD ubicacion_estado NVARCHAR(100) NULL;
IF COL_LENGTH('dim_interns','oi') IS NULL ALTER TABLE dim_interns ADD oi NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','cc') IS NULL ALTER TABLE dim_interns ADD cc NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','fecha_graduacion') IS NULL ALTER TABLE dim_interns ADD fecha_graduacion NVARCHAR(50) NULL;
IF COL_LENGTH('dim_interns','hr_list_matched') IS NULL ALTER TABLE dim_interns ADD hr_list_matched BIT NULL;
IF COL_LENGTH('dim_interns','apodo') IS NULL ALTER TABLE dim_interns ADD apodo NVARCHAR(100) NULL;
IF COL_LENGTH('dim_interns','linkedin') IS NULL ALTER TABLE dim_interns ADD linkedin NVARCHAR(300) NULL;
IF COL_LENGTH('dim_interns','documents_status') IS NULL ALTER TABLE dim_interns ADD documents_status NVARCHAR(40) NULL;
IF COL_LENGTH('dim_interns','convenio_status') IS NULL ALTER TABLE dim_interns ADD convenio_status NVARCHAR(40) NULL;

-- ── fact_intern_beneficiaries (from the alta) ────────────────────────────────────
IF OBJECT_ID('dbo.fact_intern_beneficiaries','U') IS NULL
CREATE TABLE dbo.fact_intern_beneficiaries (
  beneficiary_id NVARCHAR(50) NOT NULL PRIMARY KEY, intern_id NVARCHAR(50) NULL,
  nombre NVARCHAR(150) NULL, paterno NVARCHAR(150) NULL, materno NVARCHAR(150) NULL,
  parentesco NVARCHAR(50) NULL, porcentaje NVARCHAR(20) NULL,
  source_blob NVARCHAR(400) NULL, created_at DATETIME2 DEFAULT SYSUTCDATETIME());

-- ── dim_manager_assignments (W1 layout: jefe directo → OI/CC/compañía/UDN) ────────
IF OBJECT_ID('dbo.dim_manager_assignments','U') IS NULL
CREATE TABLE dbo.dim_manager_assignments (
  jefe_key NVARCHAR(300) NOT NULL PRIMARY KEY, jefe_directo NVARCHAR(200) NULL,
  vp NVARCHAR(200) NULL, asesor_rh NVARCHAR(200) NULL, ubicacion_udn NVARCHAR(200) NULL,
  estado NVARCHAR(100) NULL, compania NVARCHAR(200) NULL, oi NVARCHAR(50) NULL,
  cc NVARCHAR(50) NULL, updated_at DATETIME2 DEFAULT SYSUTCDATETIME());

-- ── fact_intern_documents (stages C–E document tracking) ─────────────────────────
IF OBJECT_ID('dbo.fact_intern_documents','U') IS NULL
CREATE TABLE dbo.fact_intern_documents (
  document_id NVARCHAR(50) NOT NULL PRIMARY KEY, intern_id NVARCHAR(50) NULL,
  stage NVARCHAR(30) NULL, document_type NVARCHAR(40) NULL, file_name NVARCHAR(300) NULL,
  blob_path NVARCHAR(400) NULL, name_match BIT NULL, extracted NVARCHAR(MAX) NULL,
  status NVARCHAR(40) NULL, notes NVARCHAR(MAX) NULL, created_at DATETIME2 DEFAULT SYSUTCDATETIME());
