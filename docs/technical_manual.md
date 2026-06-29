# Manual tecnico - Sistema de practicantes CEMEX

Version: 2026-06-29
Ambiente documentado: Azure dev/productivo controlado para automatizacion de practicantes
Repositorio: `/Users/bryangomezcemex/intern-system-pipeline`
Owner operativo: Bryan Gomez, CEMEX HR

Este manual esta escrito en espanol. Los nombres de servicios, variables de entorno,
tablas, vistas, columnas, comandos y archivos se mantienen en ingles cuando ese es
su nombre real en Azure, SQL, GitHub o el codigo.

## 1. Objetivo del sistema

El sistema automatiza el ciclo de vida de practicantes para CEMEX HR:

- Recibe archivos desde correo, carga manual o procesos programados.
- Guarda los archivos en Azure Blob Storage.
- Procesa cada archivo con Azure Functions y Python.
- Clasifica requisiciones, listas de altas, bases actuales, documentos y vacantes abiertas.
- Extrae datos de Excel, CSV, DOCX, PDF e imagenes.
- Usa Azure AI Document Intelligence cuando un PDF escaneado o imagen no tiene texto legible.
- Actualiza Azure SQL con practicantes, documentos, requisiciones, validaciones, comunicaciones y eventos.
- Enriquece campos organizacionales usando reglas de matching.
- Envia correos reales por Gmail SMTP cuando `EMAIL_SIMULATION_MODE=false`.
- Expone vistas limpias para Power BI sin requerir DAX complejo.

Flujo resumido:

```text
Email / Gmail intake / carga manual
  -> Azure Blob Storage: raw-uploads
  -> Azure Function: process_raw_upload
  -> Python pipeline
  -> Azure SQL operational tables
  -> Azure SQL Power BI views
  -> Power BI Service
  -> Correos Gmail SMTP cuando aplica
```

## 2. Stack completo

### Lenguajes y runtime

- Python 3.11 en Azure Functions.
- SQL / T-SQL en Azure SQL Database.
- Markdown para manuales y handoff operativo.
- Bash / Azure CLI para operacion y despliegue.

### Librerias principales de Python

- `azure-functions`
- `azure-storage-blob`
- `azure-identity`
- `pandas`
- `openpyxl`
- `pyodbc`
- `pypdf`
- `python-dotenv`
- `requests`

### Azure

- Azure Functions Flex Consumption.
- Azure Blob Storage.
- Azure SQL Database.
- Azure AI Document Intelligence.
- Azure Application Insights / Azure Monitor.
- Azure Event Grid para el trigger de blobs.
- Azure Container Instances para utilidades temporales de SQL cuando se necesita.
- Azure CLI.
- Azure Oryx Remote Build para build remoto del Function App.

### BI y operaciones

- Power BI Service.
- Azure SQL connector en Power BI.
- SQL views para reporting sin DAX.
- Git y GitHub.
- GitHub Actions.
- Docker o tooling containerizado para utilidades puntuales.

## 3. Recursos actuales en Azure

No se deben documentar ni imprimir secrets. Los valores sensibles viven en Azure
Function App settings, `.env` local o recursos de Azure.

| Tipo | Nombre actual | Uso |
|---|---|---|
| Subscription | `a3d54e37-bfef-4efb-8f09-f6d848b499c7` | Subscription CEMEX donde vive el sistema |
| Tenant | `6ee19001-...` | Tenant corporativo |
| Resource Group | `rg-intern-pipeline-dev` | Contenedor de recursos |
| Function App | `mex-intern-pipeline-func-win` | Ejecucion del pipeline |
| Plan | Flex Consumption | Escala bajo demanda |
| Azure SQL Server | `rg-intern-system-devbge.database.windows.net` | Servidor SQL |
| Azure SQL DB | `rg-intern-system-dev` | Base de datos del sistema |
| Storage Account | `rginternpipelinedevb961` | Archivos de entrada, archivo y reportes |
| Blob container | `raw-uploads` | Entrada oficial de archivos |
| Blob container | `archive` | Archivos procesados, templates y archivo historico |
| Blob container | `error-reports` | Reportes de error |
| Document Intelligence | `docintel-intern-pipeline-dev` | OCR / lectura de documentos escaneados |
| Application Insights | `mex-intern-pipeline-func-win` | Logs y monitoreo |

Estado importante de correo live:

- `EMAIL_SIMULATION_MODE=false` en el Function App live, por lo tanto los correos
  se envian realmente.
- `RH_RECIPIENT_EMAILS` esta apuntando a Bryan para pruebas controladas.
- La gestion Coparmex ya no usa un destinatario externo separado; se envia a RH
  para revision rapida y reenvio manual a Coparmex.
- El sender actual se configura con `SMTP_FROM_EMAIL` y usa el Gmail app account.
- Los recursos ACS pueden existir en Azure, pero ya no son el camino activo de
  envio de correos.

## 4. Estructura del repositorio

```text
.
├── AGENT_HANDOFF.md
├── README.md
├── azure_function_app/
│   ├── function_app.py
│   ├── host.json
│   ├── requirements.txt
│   ├── local.settings.example.json
│   ├── scripts/
│   └── sql/
├── scripts/
│   ├── pipeline_service.py
│   ├── onboarding_pipeline.py
│   ├── document_pipeline.py
│   ├── email_service.py
│   ├── flexible_file_classifier.py
│   ├── matching_engine.py
│   ├── lifecycle_requirements.py
│   ├── azure_clients.py
│   ├── app_config.py
│   ├── requisition_parser.py
│   ├── intake_gmail_attachments.py
│   ├── process_blob_file.py
│   ├── run_intake_pipeline.py
│   ├── check_function_readiness.py
│   ├── smoke_e2e_pipeline.py
│   └── sql/
├── docs/
│   ├── technical_manual.md
│   ├── hr_manual.md
│   ├── system_behavior_reference.md
│   ├── power_bi_no_dax_5_pages.md
│   ├── power_bi_dashboard.md
│   └── email_alert_recommendations.md
└── data/
```

Regla de codigo:

- `scripts/` es la fuente de verdad para modulos Python.
- `azure_function_app/scripts/` contiene copias usadas por el Function App.
- Despues de editar un modulo bajo `scripts/`, correr:

```bash
.venv/bin/python scripts/sync_function_modules.py
```

## 5. Componentes principales

### 5.1 Azure Function

Archivo: `azure_function_app/function_app.py`

Funcion principal:

```text
process_raw_upload
```

Trigger:

```text
Blob trigger con Event Grid
Container: raw-uploads
Path: raw-uploads/{name}
Connection: AZURE_STORAGE_CONNECTION_STRING
```

Comportamiento:

1. Recibe el evento de creacion del blob.
2. Limpia el nombre para quitar el prefijo del container.
3. Ignora rutas internas.
4. Llama `process_blob_by_name(...)` en `pipeline_service.py`.
5. Registra exito o error en logs de Azure Functions.

Rutas ignoradas:

```text
archive/
processed/
failed/
error-reports/
.
```

Tambien existen funciones HTTP administrativas para setup de SQL:

- `setup_database`
- `setup_database_on_startup`

Estas rutas solo deben usarse si `ENABLE_ADMIN_SQL_SETUP` esta activado
intencionalmente.

### 5.2 Pipeline principal

Archivo: `scripts/pipeline_service.py`

Responsabilidades:

- Leer blobs desde `raw-uploads`.
- Evitar reprocesamiento con guardas de blob procesado.
- Clasificar archivos.
- Extraer filas y campos.
- Hacer upsert en Azure SQL.
- Detectar bajas por cambio de status.
- Crear eventos de ciclo de vida.
- Registrar validaciones y faltantes.
- Preparar y enviar comunicaciones cuando aplica.
- Crear paquetes o referencias de documentos.

Funciones clave:

- `process_blob_by_name`
- `process_next_blob`
- `process_all_pending_blobs`
- `run_pipeline_for_uploaded_file`
- `resolve_group_recipients`
- `prepare_baja_communication`
- `build_baja_email_subject`
- `build_baja_email_body`

### 5.3 Onboarding

Archivo: `scripts/onboarding_pipeline.py`

Responsabilidades:

- Procesar requisiciones.
- Procesar listas de nuevos ingresos de RH.
- Enviar Paquete 1.
- Procesar documentos del candidato.
- Procesar convenio y NDA.
- Enviar correos de avance.
- Preparar informacion para Coparmex.
- Procesar la lista de posiciones abiertas.

Tipos principales que reconoce:

```text
requisicion
hr_new_hires
alta_candidate
open_positions
documentos
```

### 5.4 Documentos

Archivo: `scripts/document_pipeline.py`

Responsabilidades:

- Clasificar documentos por filename y contenido.
- Leer texto de PDFs con capa de texto.
- Usar Document Intelligence para PDFs escaneados o imagenes.
- Asociar documentos con el practicante correcto.
- Validar CURP y otros datos cuando estan disponibles.
- Detectar documentos faltantes del Paquete 1.

Document Intelligence usa el modelo:

```text
prebuilt-read
api-version=2023-07-31
```

### 5.5 Matching organizacional

Archivo: `scripts/matching_engine.py`

El sistema usa relaciones de HR para completar o validar campos organizacionales.

Jerarquia principal:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

`JefeInmediato` no es parte formal de la jerarquia, pero es una senal fuerte de
matching.

Relaciones fuertes:

```text
JefeInmediato -> VP HC
JefeInmediato -> CC HC
JefeInmediato -> OI HC
OI HC -> VP HC
OI HC -> CC HC
CC HC -> VP HC
CC HC -> CIA HC
```

Uso practico:

- Si una fila trae `JefeInmediato`, se usa para sugerir o validar `VP HC`, `CC HC`,
  `OI HC` y `CIA HC`.
- Si una fila trae `OI HC`, se usa para inferir `VP HC` y `CC HC` cuando faltan.
- Si una fila trae `CC HC`, se usa para inferir `VP HC` y `CIA HC` cuando faltan.
- Si un campo esta vacio, el sistema intenta llenarlo con la relacion mas fuerte
  disponible para esa fila.

## 6. Tipos de archivos soportados

### 6.1 Requisiciones

Formato esperado:

- DOCX principalmente.
- Puede venir desde correo con metadata.

Datos importantes:

- `sender_email`
- `email_subject`
- `body_fields`
- `requisition_id` o position id si existe

Resultado:

- Se crea o actualiza una requisicion.
- Se genera un ID tipo `REQ-YYYY-NNNN` cuando aplica.
- Se manda confirmacion al solicitante si el flujo esta completo.

### 6.2 Lista de nuevos ingresos de RH

Formato:

- Excel o CSV.

Uso:

- Crear el registro inicial del nuevo practicante.
- Asociarlo con requisicion / position id cuando existe.
- Enviar Paquete 1 al correo personal del candidato.

### 6.3 Paquete 1

Nombre de negocio:

```text
Paquete 1
```

Documentos requeridos:

- Alta / formato de datos.
- CURP.
- Constancia de estudios.
- Identificacion.
- Comprobante de domicilio.
- Acta de nacimiento.

Documentos removidos u opcionales:

- Foto profesional ya no es requerida.

Dato adicional solicitado por email:

- Contacto de emergencia: nombre, parentesco y telefono.

### 6.4 Convenio y NDA

Flujo:

1. RH carga convenio y NDA.
2. El convenio se envia al candidato solo como copia.
3. El NDA se debe cargar en DOCX y se envia al candidato para firma.
4. El candidato regresa solamente el NDA firmado en PDF.
5. El sistema valida que el NDA firmado sea PDF.
6. RH recibe aviso con el NDA firmado adjunto.

### 6.5 Base actual de practicantes

Formato:

- Excel o CSV.
- Ejemplo fuente: W1 / layout de practicantes.

Uso:

- Actualizar activos e inactivos.
- Detectar cambios de status.
- Detectar contratos vencidos.
- Actualizar costos `importe` e `importe_total`.
- Actualizar campos organizacionales.

Regla de costo:

- `importe` = pago del practicante.
- `importe_total` = costo total para la compania.
- Si falta `importe_total`, algunas vistas pueden usar aproximacion basada en
  `salario_mensual x 1.1` hasta re-subir el roster completo con columnas reales.

### 6.6 Lista de posiciones abiertas

Formato:

- Excel o CSV.

Columnas esperadas:

- `#`
- `Vacante`
- `ID Vacante`
- `Ubicacion`
- `Promedio Dias Abierto`
- `Responsable`
- `AIRH`
- `Jefe del Puesto`
- `Estatus General`

Tabla:

```text
dim_open_positions
```

Vista Power BI:

```text
vw_powerbi_posiciones_abiertas
```

Cada upload reemplaza el snapshot actual marcando registros anteriores como
`is_current = 0` y cargando la nueva version como `is_current = 1`.

## 7. Azure Blob Storage

Container de entrada:

```text
raw-uploads
```

Containers de soporte:

```text
archive
error-reports
```

Rutas recomendadas:

```text
current_interns/YYYY/MM/file.xlsx
requisitions/YYYY/MM/file.docx
candidate_docs/YYYY/MM/file.pdf
open_positions/YYYY/MM/file.xlsx
unknown/YYYY/MM/file.xlsx
```

Notas:

- La clasificacion puede funcionar aunque la carpeta no sea perfecta.
- Nombres descriptivos facilitan auditoria.
- Los archivos procesados no deben volver a subirse con el mismo nombre si se
  desea forzar reprocesamiento sin limpiar guardas.

## 8. Azure SQL

### 8.1 Orden de scripts para una base nueva

Los scripts viven en `scripts/sql/` y deben ejecutarse separando batches por `GO`.

Orden actual:

```text
00_create_core_legacy_tables.sql
00_create_dim_interns.sql
create_full_mvp_pipeline.sql
fix_file_id_source_file_id_compatibility.sql
seed_pipeline_validation_rules.sql
2026-06_package1_document_requirements.sql
2026-06_resolve_stale_missing_items.sql
add_corporate_column_aliases.sql
create_matching_engine_v1.sql
create_business_powerbi_views.sql
2026-06_onboarding_schema.sql
2026-06_schema_simplification.sql
2026-06_powerbi_no_dax_views.sql
2026-06_powerbi_refinements.sql
2026-06_open_positions.sql
2026-06_cost_columns.sql
```

El Function App tambien mantiene este orden en `SQL_SETUP_ORDER`.

### 8.2 Tablas operativas principales

Nombres importantes:

- `dim_interns`
- `dim_documents`
- `dim_document_types`
- `dim_requisitions`
- `dim_open_positions`
- `dim_manager_assignments`
- `dim_email_recipients`
- `dim_recipient_groups`
- `fact_pipeline_runs`
- `fact_processed_blobs`
- `fact_validations`
- `fact_intern_missing_items`
- `fact_intern_lifecycle_events`
- `fact_communications`
- `fact_document_validations`
- `fact_process_requirements`

La tabla exacta puede variar por compatibilidad historica. Para inventario completo,
usar:

```sql
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_SCHEMA, TABLE_NAME;
```

Columnas por tabla:

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
```

### 8.3 Vistas recomendadas para Power BI

Vistas canonicas:

- `vw_canonical_interns_current`
- `vw_canonical_intern_documents`
- `vw_canonical_document_types`
- `vw_canonical_org_assignments`
- `vw_canonical_requisitions`
- `vw_canonical_pipeline_runs`

Vistas operativas / negocio:

- `vw_business_validation_exceptions`
- `vw_requisitions_status`
- `vw_communications_status`
- `vw_hr_actions_today`

Vistas Power BI:

- `vw_powerbi_dashboard_kpis`
- `vw_powerbi_vp_summary`
- `vw_powerbi_location_summary`
- `vw_powerbi_contract_risk`
- `vw_powerbi_document_status`
- `vw_powerbi_document_summary`
- `vw_powerbi_hr_action_queue`
- `vw_powerbi_vacantes`
- `vw_powerbi_costos_practicantes`
- `vw_powerbi_expired_active_contracts`
- `vw_powerbi_inactive_interns`
- `vw_powerbi_vp_capacity`
- `vw_powerbi_posiciones_abiertas`

Las vistas `vw_full_mvp_*` pueden existir por compatibilidad, pero para reportes
nuevos se deben preferir `vw_powerbi_*` y `vw_canonical_*`.

## 9. Correos

### 9.1 Proveedor

Proveedor actual:

```text
Gmail SMTP
```

Archivo:

```text
scripts/email_service.py
```

No se usa Power Automate para el flujo actual. El sistema live usa Gmail IMAP
para intake programado y Gmail SMTP para envio.

### 9.2 Variables principales

```text
EMAIL_PROVIDER=smtp
EMAIL_SIMULATION_MODE=true|false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<gmail address>
SMTP_PASSWORD=<gmail app password>
SMTP_FROM_EMAIL=<gmail address>
SMTP_FROM_NAME=Programa de Practicantes CEMEX
ENABLE_GMAIL_INTAKE=true
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=<gmail address>
IMAP_PASSWORD=<gmail app password>
INTAKE_EMAIL_FOLDER=INBOX
INTAKE_SUBJECT_TAG=
GMAIL_INTAKE_MAX_PENDING_BLOBS=25
RH_RECIPIENT_EMAILS=<lista de correos>
POWERBI_DASHBOARD_URL=<url del reporte>
```

Regla de seguridad:

- `EMAIL_SIMULATION_MODE=true` nunca envia correos reales.
- `EMAIL_SIMULATION_MODE=false` envia correos reales.
- En el ambiente live actual esta en `false`, por lo que cualquier deploy o prueba
  que dispare flujo de email puede mandar correos reales.

### 9.3 Correos principales del flujo

| Evento | Destinatario | Subject base | Estado |
|---|---|---|---|
| Requisicion recibida | Solicitante | `Requisición recibida - ID de posición ...` | Live |
| Error / devolucion | Solicitante o candidato | `Devolución: ...` | Live |
| Paquete 1 | Candidato | `¡Te damos la bienvenida a Cemex! Paquete 1 - Summer Internship Program` | Live |
| Documentos recibidos | Candidato | `Documentos recibidos - Summer Internship Program` | Live |
| Convenio / NDA | Candidato | `¡Te damos la bienvenida a Cemex! Documentos - Summer Internship Program` | Live |
| NDA firmado recibido | RH | `NDA firmado recibido` | Live, incluye PDF adjunto |
| Finalizacion | Practicante | `Gracias - Summer Internship Program` | Live |
| Gestionar convenio Coparmex | RH | `FAVOR DE GESTIONAR CONVENIO - {nombre}` | Live, RH revisa y reenvia |
| Alta exitosa | RH | `Practicante dado de alta exitosamente` | Live |
| Datos faltantes para gestion Coparmex | RH | `Practicante procesado - faltan datos para Coparmex (...)` | Live, caso raro si matching no resolvio |
| Campos organizacionales no resueltos | RH | `Campos organizacionales por completar - {archivo}` | Live, incluye Excel adjunto |
| Baja | RH | `Baja De Practicante - {nombre}` | Live, best-effort |

### 9.4 Attachments

Gmail SMTP soporta attachments via `email_service._build_attachments`.

Soportes:

- Rutas de archivo local.
- Tuplas `(name, bytes)`.

Si un attachment no se puede leer, se omite y se registra nota en logs; no debe
tumbar todo el envio.

## 10. Bajas

La baja se detecta durante la sincronizacion de la base actual de practicantes.

Condicion:

```text
status anterior: activo / active / ST002
status nuevo: baja / inactivo / inactive / ST003 / ST004
```

Efectos:

1. El practicante deja de contar como activo.
2. Se crea evento en `fact_intern_lifecycle_events`.
3. Se prepara comunicacion en `fact_communications`.
4. Se intenta enviar correo real a RH por Gmail SMTP si `EMAIL_SIMULATION_MODE=false`.

Subject:

```text
Baja De Practicante - {nombre}
```

El body incluye datos personales, academicos, CEMEX, organizacionales, sueldo,
fecha de ingreso, fecha fin y estado.

## 11. Validaciones

### 11.1 Datos del candidato

Validaciones principales:

- Nombre requerido.
- Email con formato valido.
- CURP con formato de 18 caracteres.
- Carrera requerida.
- Fecha de nacimiento no futura.
- Advertencia si carrera no coincide con requisicion.

### 11.2 Documentos

Validaciones principales:

- Tipo de documento requerido.
- Clasificacion por filename y contenido.
- CURP de documento vs alta cuando esta disponible.
- Texto leible o OCR por Document Intelligence.
- Documentos requeridos completos.
- NDA original de RH en DOCX.
- NDA firmado del practicante en PDF.
- Nombre de archivo firmado para NDA cuando aplica.

### 11.3 Contratos

Validaciones principales:

- Activo con contrato vencido.
- Activo con contrato por vencer en 30 dias.
- Inactivo/baja que todavia aparezca en activos.

## 12. Power BI

Power BI debe conectarse a Azure SQL y consumir vistas, no tablas crudas.

Modo recomendado:

```text
Import mode + scheduled refresh
```

Refresh recomendado:

- Cada 30 minutos o 1 hora durante operacion.
- Diario si el volumen es bajo.

Paginas recomendadas:

1. Resumen Ejecutivo.
2. Vacantes y Capacidad.
3. Costos.
4. Contratos, Bajas e Inactivos.
5. Documentos y Excepciones.

Detalle completo de visuales:

```text
docs/power_bi_no_dax_5_pages.md
docs/power_bi_dashboard.md
```

## 13. Configuracion local

Archivo local:

```text
.env
```

Nunca commitear `.env`.

Variables minimas para pruebas locales con Azure:

```text
AZURE_STORAGE_CONNECTION_STRING=<secret>
RAW_UPLOADS_CONTAINER=raw-uploads
ERROR_REPORTS_CONTAINER=error-reports
ARCHIVE_CONTAINER=archive
AZURE_SQL_SERVER=<server>
AZURE_SQL_DATABASE=<database>
AZURE_SQL_AUTH_MODE=interactive|sql_password|managed_identity
AZURE_SQL_CONNECTION_STRING=<secret cuando aplique>
EMAIL_SIMULATION_MODE=true
DEV_EMAIL_OVERRIDE=<correo de prueba>
DOC_INTEL_ENDPOINT=<endpoint>
DOC_INTEL_KEY=<secret>
```

Compilar modulos:

```bash
.venv/bin/python -m py_compile scripts/process_blob_file.py scripts/pipeline_service.py scripts/run_intake_pipeline.py scripts/flexible_file_classifier.py scripts/lifecycle_requirements.py scripts/matching_engine.py scripts/communication_packager.py scripts/check_function_readiness.py scripts/smoke_e2e_pipeline.py scripts/deployment_readiness_e2e.py scripts/onboarding_pipeline.py scripts/document_pipeline.py scripts/requisition_parser.py scripts/email_service.py
```

Readiness check:

```bash
.venv/bin/python scripts/check_function_readiness.py
```

Smoke test offline:

```bash
.venv/bin/python scripts/smoke_e2e_pipeline.py
```

Smoke con revision de vistas SQL:

```bash
SMOKE_CHECK_SQL_VIEWS=1 .venv/bin/python scripts/smoke_e2e_pipeline.py
```

## 14. Despliegue

El Function App es Flex Consumption. Usar zip deploy con build remoto:

```bash
cd azure_function_app
zip -r /tmp/mex-intern-pipeline.zip . \
  -x '*.pyc' '__pycache__/*' '*/__pycache__/*' '.DS_Store' \
     'local.settings.json' '.env' '.venv/*'

az functionapp deployment source config-zip \
  -g rg-intern-pipeline-dev \
  -n mex-intern-pipeline-func-win \
  --src /tmp/mex-intern-pipeline.zip \
  --build-remote true
```

Reiniciar si aplica:

```bash
az functionapp restart \
  -g rg-intern-pipeline-dev \
  -n mex-intern-pipeline-func-win
```

Nota:

- Classic Kudu `/api/zipdeploy` no funciona correctamente para este Flex app.
- Enviar source solamente; Azure Oryx instala dependencias en build remoto.
- Deploys productivos requieren aprobacion explicita de Bryan.

## 15. Monitoreo y troubleshooting

### 15.1 Function App

Revisar estado:

```bash
az functionapp show \
  -g rg-intern-pipeline-dev \
  -n mex-intern-pipeline-func-win \
  --query "{state:state, hostNames:enabledHostNames}"
```

Listar funciones:

```bash
az functionapp function list \
  -g rg-intern-pipeline-dev \
  -n mex-intern-pipeline-func-win \
  --query "[].name"
```

### 15.2 SQL

Validar tablas:

```sql
SELECT COUNT(*) AS table_count
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_TYPE = 'BASE TABLE';
```

Validar vistas Power BI:

```sql
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME LIKE 'vw_powerbi_%'
ORDER BY TABLE_NAME;
```

Validar runs recientes:

```sql
SELECT TOP 50 *
FROM dbo.fact_pipeline_runs
ORDER BY started_at DESC;
```

### 15.3 Storage

Validar containers:

```bash
az storage container list \
  --account-name rginternpipelinedevb961 \
  --query "[].name"
```

### 15.4 Email

Validar modo de envio sin imprimir secrets:

```bash
az functionapp config appsettings list \
  -g rg-intern-pipeline-dev \
  -n mex-intern-pipeline-func-win \
  --query "[?name=='EMAIL_SIMULATION_MODE' || name=='RH_RECIPIENT_EMAILS' || name=='SMTP_FROM_EMAIL' || name=='SMTP_USERNAME'].{name:name,value:value}"
```

Interpretacion:

- `EMAIL_SIMULATION_MODE=true`: no manda correos reales.
- `EMAIL_SIMULATION_MODE=false`: manda correos reales.

## 16. Seguridad

Reglas:

- Nunca commitear `.env`, connection strings, SQL passwords, Gmail app passwords ni Document Intelligence keys.
- Nunca imprimir secrets completos en terminal o en manuales.
- Usar Function App settings para secretos en Azure.
- Usar `.env` solo localmente.
- Rotar cualquier secreto que haya sido expuesto.
- Mantener `ROTATE_SECRETS.md` como registro de credenciales que Bryan debe rotar.
- Confirmar con Bryan antes de deploy productivo, cambios live de schema o merges a `main`.

## 17. Costos aproximados

El costo depende del uso, pero para el volumen actual el estimado mensual es bajo.

| Servicio | Cobro principal | Estimado mensual bajo uso |
|---|---|---|
| Azure SQL Basic | DB provisionada | aprox. 5 USD |
| Azure Functions Flex | ejecuciones y memoria | 0 a 2 USD |
| Blob Storage Hot LRS | GB almacenado y operaciones | menos de 1 USD con pocos MB |
| Document Intelligence F0 | free tier | 0 USD mientras siga en F0 y dentro del limite |
| Gmail SMTP | incluido en Gmail, sujeto a limites de envio | 0 USD directo; depende de la cuenta |
| Application Insights | ingesta de logs | 0 a 5 USD si el volumen es bajo |

Estimado total actual:

```text
6 a 15 USD / mes aproximadamente
```

## 18. Pendientes conocidos

- Re-subir el roster W1 completo con las 302 filas y columnas reales `Importe` /
  `ImporteTotal` para eliminar aproximaciones de costo.
- Mantener y rotar el Gmail app password usado para intake/envio.
- Configurar CI/CD con OIDC para que GitHub Actions despliegue Flex correctamente.
- Decidir si se quiere digest programado de contratos vencidos / activos para RH.
- Decidir si `dim_open_positions` debe registrar runs formales tipo `PROC_POSITIONS_SYNC`.
- Resolver fisicamente `fact_intern_missing_items` cuando matching completa campos,
  si se quiere que SQL operativo cierre esos items y no solo las vistas los muestren
  como `Resuelta automaticamente`.

## 19. Regla de oro operativa

Si cambia el nombre de cualquier recurso, actualizar estos lugares:

- Azure Function App settings.
- Azure SQL permissions / connection.
- Power BI connection.
- `.env` local.
- Documentacion en `docs/`.
- Comandos de deploy.
- `AGENT_HANDOFF.md`.
