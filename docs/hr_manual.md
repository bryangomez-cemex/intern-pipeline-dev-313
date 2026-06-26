# Manual de RH - Sistema de practicantes CEMEX

Fecha: 2026-06-26

Este manual explica como usar el sistema desde el punto de vista de RH. No requiere
conocer codigo. Los nombres tecnicos estan en ingles para mejor referencia.

## 1. Que hace el sistema

El sistema ayuda RH operar el ciclo de practicantes:

- Recibe requisiciones.
- Crea posiciones o IDs desde requisicion.
- Procesa Excels de nuevos practicantes.
- Manda el Paquete 1 (Alta Excel) al candidato.
- Valida documentos.
- Detecta documentos faltantes.
- Prepara informacion para Coparmex los cuales se envian a RH.
- Manda el Paquete 2 (Alta Procesada, NDA) al candidato.
- Detecta bajas cuando un practicante cambia de activo a inactivo/baja.
- Detecta contratos vencidos o por vencer.
- Actualiza Power BI con activos, vacantes, costos, inactivos, documentos y capacidad por VP.

## 2. Donde se ve la informacion

La informacion principal se consulta en Power BI.

Paginas recomendadas:

1. Resumen Ejecutivo.
2. Vacantes y Capacidad.
3. Costos.
4. Vencimientos.
5. Quality.

## 3. Que archivos puede recibir el sistema

### Requisicion

Uso:

- Abrir una posicion de practicante.
- Generar o asociar ID tipo `REQ-YYYY-NNNN`.

Recomendaciones:

- Enviar el archivo de requisicion en DOCX.
- Incluir en el correo informacion clara del solicitante y posicion.
- Si ya existe ID de requisicion o Posicion, incluirlo en subject o cuerpo.

Ejemplo de subject:

```text
Requisicion practicante - <area o puesto>
```

Si ya hay ID:

```text
REQ-2026-0001 - Requisicion practicante - <area o puesto>
```

El sistema no depende de un subject fijo; usa adjuntos, metadata del correo,
cuerpo del mensaje, remitente y IDs cuando vienen disponibles.

### Lista de nuevos ingresos

Uso:

- Dar de alta candidatos aceptados.
- Enviar Paquete 1 automaticamente.

Recomendacion:

- Enviar Excel o CSV.
- Incluir al menos: nombre completo, correo personal y cualquier ID de posicion/requisicion disponible.
- Preferibles: Ya mencionados mas puesto/proyecto, jefe directo, VP, ubicacion, fechas
- Mientras mas completo venga el archivo, menos correcciones pedira el sistema.

### Paquete 1 del candidato

El candidato debe mandar:

- Alta / formato de datos.
- CURP.
- Constancia de estudios.
- Identificacion.
- Comprobante de domicilio.
- Acta de nacimiento.

Tambien debe responder en el texto del correo:

- Contacto de emergencia: nombre, parentesco y telefono.

### Convenio y NDA

Uso:

- RH carga convenio y NDA cuando Paquete 1 ya esta completo.
- El convenio se envia solo para que el practicante tenga una copia.
- El NDA se debe cargar en DOCX.
- El sistema manda convenio y NDA al candidato.
- El candidato regresa solamente el NDA firmado en PDF.
- RH recibe aviso cuando el NDA esta firmado y el sistema lo manda adjunto a RH.

### Base actual de practicantes

Uso:

- Actualizar activos, inactivos, bajas, fechas, costos y estructura organizacional.

Recomendacion:

- Usar el archivo mas actualizado de coparmex layout u otros.
- Incluir las 3 paginas del layout

### Lista de posiciones abiertas

Uso:

- Mostrar en Power BI posiciones sin practicante asignado.
- Si una posicion ya tiene practicante asignado, debe dejar de aparecer como abierta
  cuando la fuente actualizada ya no la marque como vacante.

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

## 4. Flujo de onboarding

### Paso 1 - Requisicion

RH o el solicitante envia la requisicion.

El sistema:

- Lee el archivo.
- Crea o confirma el ID de posicion.
- Responde al solicitante con el ID cuando aplica.

### Paso 2 - Lista de nuevo ingreso

RH manda la lista de candidatos aceptados.

El sistema:

- Crea el registro del candidato.
- Hace matching con requisicion, correo, nombre o position id.
- Envia Paquete 1 al candidato.

### Paso 3 - Candidato manda Paquete 1

El candidato responde con documentos y datos.

El sistema:

- Clasifica documentos.
- Lee contenido.
- Usa OCR si el archivo es escaneado o imagen.
- Revisa documentos requeridos.
- Guarda cuales archivos faltan.
- Si falta algo, manda devolucion.
- Si esta completo, confirma recepcion.

### Paso 4 - Convenio y NDA

RH carga convenio y NDA.

El sistema:

- Manda el convenio al candidato solo como copia.
- Manda el NDA al candidato en DOCX para firma.
- Espera que el practicante regrese solamente el NDA firmado en PDF.
- Confirma a RH cuando el NDA este firmado y se lo manda adjunto a RH.

### Paso 5 - Cierre / Coparmex

Cuando el expediente esta listo:

- El candidato recibe correo de cierre.
- RH recibe aviso de alta exitosa.
- Si estan todos los datos requeridos, se prepara la gestion Coparmex y se envia a RH.
  RH le da una revision rapida y lo reenvia a Coparmex.
- Si falta algun dato requerido que el sistema no pudo resolver automaticamente,
  RH recibe correo con los faltantes. Esto deberia ser un caso raro.

## 5. Bajas

La baja se detecta cuando la base actualizada cambia un practicante de activo a
inactivo/baja.

El sistema:

- Lo quita del conteo de activos.
- Registra evento de baja.
- Manda correo a RH.

Subject:

```text
Baja De Practicante - <NOMBRE DE PRACTICANTE>
```

El correo incluye:

- Fecha de nacimiento.
- Correo personal.
- Universidad.
- Carrera.
- Semestre.
- Fecha de graduacion.
- CEMEX-ID.
- Correo institucional CEMEX.
- Vicepresidencia.
- Nombre del proyecto.
- Jefe directo.
- AIRH.
- Ubicacion UDN.
- Compania.
- OI.
- CC.
- Sueldo.
- Fecha de ingreso.
- Fecha fin.
- Estado de practicante.
- Nombre completo.

Accion de RH:

- Gestionar baja en los sistemas correspondientes.
- Confirmar si era baja real o si debe corregirse como extension/activo.

## 6. Contratos vencidos y por vencer

Power BI muestra:

- Practicantes activos con contrato vencido.
- Practicantes activos con contrato por vencer.
- Inactivos/bajas.

Acciones esperadas:

- Si sigue trabajando: gestionar extension y actualizar fecha fin.
- Si ya termino: marcar baja/inactivo en la siguiente base.
- Si el dato esta mal: corregir archivo fuente y reenviar.

## 7. Documentos faltantes

Power BI y los correos de devolucion indican documentos faltantes.

Acciones esperadas:

- Solicitar al practicante el documento indicado.
- Reenviar el archivo con nombre claro.
- Evitar imagenes borrosas, cortadas o ilegibles.
- Si es PDF escaneado, el sistema intenta leerlo con Document Intelligence, pero
  la calidad del documento sigue importando.

## 8. Campos organizacionales

Jerarquia usada:

```text
CIA HC -> VP HC -> CC HC -> OI HC
```

`JefeInmediato` ayuda a validar o completar datos, pero no es una capa formal de
la jerarquia.

Si faltan campos, el sistema intenta completarlos usando relaciones conocidas:

- `JefeInmediato` con VP, CC, OI y CIA.
- `OI HC` con VP y CC.
- `CC HC` con VP y CIA.

Accion de RH:

- Si Power BI muestra una excepcion pendiente, corregir el archivo fuente.
- Si aparece como `Resuelta automaticamente`, normalmente no requiere accion.

## 9. Power BI

### Overview

- HC activos.
- Terminaciones cercanas.
- Practicantes con documentos faltantes.
- Distribucion por VP.
- Distribucion por ubicacion.

### Vacantes & Capacidad

- Posiciones abiertas.
- Practicantes actuales por VP.
- Limite permitido por VP.
- Practicantes restantes por VP.
- VPs sobre capacidad o cerca del limite.

### Costos

- `importe_total` por VP.
- `importe_total` por ubicacion.
- `importe_total` por estado de ubicacion.
- `importe_total` por `CIA HC`.

### Vencimientos

- Activos con contrato vencido.
- Contratos por vencer.
- Todos los inactivos.
- Bajas recientes.

### Quality

- Documentos faltantes.
- Errores de validacion.
- Excepciones pendientes.
- Excepciones resueltas automaticamente.

## 10. Como saber si un archivo se proceso

Senales positivas:

- Aparece o se actualiza informacion en Power BI despues del refresh.
- El solicitante/candidato/RH recibe correo automatico.
- El archivo deja de estar pendiente en el flujo de procesamiento.

Si no aparece:

1. Verificar que el archivo se envio al correo/proceso correcto.
2. Confirmar que el correo traia los adjuntos correctos y que el cuerpo incluia
   datos utiles como requisition id, position id, nombre o correo del practicante.
3. Revisar si Power BI ya hizo refresh.
4. Revisar si RH recibio correo de devolucion.
5. Escalar a soporte tecnico con nombre del archivo, fecha/hora de envio y remitente.

## 11. Buenas practicas para RH

- Usar archivos actualizados y oficiales.
- No cambiar nombres de columnas si no es necesario.
- Incluir IDs de requisicion o posicion siempre que existan.
- No mandar varias versiones del mismo archivo con nombres identicos.
- Enviar documentos del candidato con nombres claros.
- Mantener correos personales correctos antes del Paquete 1.
- Validar que fechas de ingreso y fin esten completas.
- Para bajas, actualizar status en la base fuente y reenviar el archivo actualizado.
- Para costos, incluir `Importe` e `ImporteTotal` reales en los archivos que usualmente lo incluyan.

## 12. Preguntas frecuentes

### Si mando un email, se procesa automaticamente?

Si el intake de correo esta activo y el correo/archivo llega a `raw-uploads` en azure, si.
El trigger de Azure procesa el blob casi de inmediato. Si el correo se queda fuera
del intake o no trae archivos validos, no se procesara.

### Power Automate se usa?

No en el camino actual. El sistema opera con carga a Blob Storage, Azure Function,
Python, Azure SQL, ACS Email y Power BI.

### Como se validan los documentos antes de ser analizados?

El sistema intenta leerlo con Azure AI Document Intelligence. Si la imagen o archivo es de
mala calidad, puede requerir correccion manual o reenvio.

### Que pasa si faltan campos como VP, CC, OI o CIA?

El sistema intenta completarlos con matching organizacional. Si no puede resolverlos
con suficiente confianza, manda a RH un Excel con las filas afectadas y columnas
suficientes para completarlo manualmente. RH debe completar la base/archivo fuente
y devolverlo al sistema para que se actualice.

### Quien recibe correos de RH/Coparmex actualmente?

Por ahora los correos de RH y las gestiones Coparmex se envian solo al correo
CEMEX de Bryan. Para cambiar receptores, consultar el manual tecnico.

### Cuando se actualiza Power BI?

Diario 

## 13. Escalamiento a soporte tecnico

Cuando algo falle, enviar esta informacion:
- Nombre del archivo.
- Fecha y hora aproximada de envio.
- Remitente.
- Tipo de archivo: requisicion, nuevo ingreso, Paquete 1, base actual, vacantes.
- Screenshot o texto del error si hubo correo de devolucion.
- Si se esperaba un correo automatico, indicar quien debia recibirlo.
- Si el problema es Power BI, indicar pagina y visual afectado.
