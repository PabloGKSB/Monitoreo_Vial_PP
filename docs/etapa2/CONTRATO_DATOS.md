# Contrato de datos y relojes

Version documental 0.1. Dos perfiles distintos: LEGACY observado y V1 propuesto.
No se declara que el loader actual implemente el perfil V1.

## 1. LEGACY: Sensor Logger + Anotador

Entradas actuales: un ZIP Sensor Logger y un CSV externo Anotador, asociados por
manifiesto explicito, nunca por similitud de nombres. Ver
[configuracion real](../../configs/campana_2026_09_25_retraso_2_5.json).
route_id actual identifica grabacion; corridor_id agrupa ida/vuelta. La futura
Session distinguira ambos conceptos. No unir usando trip_id textual de apps distintas.

| Archivo/columna | Tipo y unidad del perfil | Uso / validacion |
|---|---|---|
| Accelerometer.csv, TotalAcceleration.csv, Gyroscope.csv | CSV con time, seconds_elapsed, x, y, z | Piloto requiere los tres; V0 requiere acelerometro y GPS. |
| time | Epoch entero, ns en campaña observada | Conservar original; helper infiere unidad por magnitud para fechas contemporaneas. |
| seconds_elapsed | Segundos decimales | Origen propio de Sensor Logger, no del Anotador. |
| x/y/z aceleracion | m/s2 | Mantener marco del dispositivo; no llamar z vertical vial sin transformacion validada. |
| x/y/z giro | rad/s | Derivada es aceleracion angular, no jerk lineal. |
| Location.csv | time, seconds_elapsed, latitude, longitude | Rango lat [-90,90], lon [-180,180]; invalidos no se usan. |
| speed / horizontalAccuracy | m/s / m, si disponibles | gps.py convierte velocidad a km/h; faltantes no se convierten en cero. |
| Metadata.csv | recording epoch time (ms), recording time, recording timezone | Nombre normalizado recordingepochtime en memoria; texto solo fallback. |
| CSV Anotador | trip_id,timestamp,epoch_ms,elapsed_ms,event_type | Formato observado y generado por MainActivity.kt. |
| epoch_ms Anotador | Entero ms UTC | Hora de pulsacion, NO impacto. Finito e integral. |
| elapsed_ms Anotador | Entero ms desde inicio monotono de su sesion | Solo duracion interna; no se iguala a seconds_elapsed de Sensor Logger. |
| timestamp Anotador | Texto local sin zona | Presentacion, no fuente de sincronizacion. |
| event_type | Texto | Inicio/fin mas BACHE, CAMINO_MALO, LOMO_DE_TORO, GIRO, OTRO observados. Otros tipos requieren mapping explicito. |

CSV: preservar bytes RAW, incluso BOM/encabezados originales. La exportacion
normalizada propuesta usa UTF-8, coma, punto decimal y comillas CSV estandar.
El loader admite aliases y nombres anidados; eso no prueba compatibilidad con
cualquier exportador ni semantica identica de aceleracion lineal/total.

## 2. Reloj comun y prioridad actual

En el piloto: t_s = (epoch_muestra - epoch_origen_sensor_logger) en segundos.
Para anotaciones: t_marca = (epoch_ms_marca - epoch_ms_origen) / 1000.
En codigo ambas operaciones usan timestamps UTC, respetando las unidades.
La prioridad del loader es epoch de muestra; si falta, epoch de metadata +
tiempo transcurrido; texto localizado solo como ultimo recurso. El piloto exige
epoch de acelerometro y renormaliza sensores a un origen comun antes de GPS.

Ejemplo real: origen Monte Oscuro 1790372910197 ms = 2026-09-25T21:48:30.197Z,
equivalente a 18:48:30.197 America/Santiago. No volver a interpretar el epoch
como hora local. UTC en calculos; zona solo para visualizacion.

Limitacion conocida: cuando falta seconds_elapsed, _prepare_frame infiere su
escala solo para ns/ms. El helper de timestamps acepta mas unidades, pero esto
NO convierte al loader completo en soporte general s/us. Para campaña actual
existe seconds_elapsed; el contrato V1 evitara inferencia mediante unidades explicitas.

Regla futura: capturar ancla epoch_ms + monotonic_ns y conservar ambos. Duraciones
desde monotono; UTC aproximado = ancla_epoch + (monotono - ancla_monotona)/1e6.
Registrar salto de reloj civil; no corregirlo silenciosamente ni alinear apps
de dispositivos distintos sin estimacion independiente de offset y deriva.
Anotador usa currentTimeMillis y elapsedRealtime por separado; no se midio su
latencia. Compartir dispositivo no demuestra sincronizacion perfecta.

## 3. Perfil V1 propuesto para APK propia

Paquete ZIP sin rutas absolutas ni ../, con estructura fija:

```text
session.json
streams/accelerometer.csv
streams/gyroscope.csv        (si disponible)
streams/gravity.csv          (si disponible)
location.csv
annotations.csv
checksums.json
```

session.json: schema_version="1.0", session_id UUID, device_id pseudonimo,
vehicle_id pseudonimo, corridor_id, direction, pass_index, capture_state,
started_at_utc, ended_at_utc nullable, epoch_anchor_ms, monotonic_anchor_ns,
sensor_descriptors (tipo/unidad/marco/rango/resolucion/tasa solicitada),
protocol_version, mount_state, app_version y missing_fields.

streams: session_id, sequence_no, sensor_type, monotonic_ns, epoch_ms, x,y,z,
accuracy nullable. location: session_id, sequence_no, monotonic_ns, epoch_ms,
latitude_deg,longitude_deg,speed_m_s,horizontal_accuracy_m,bearing_deg.
annotations: annotation_id,session_id,button_epoch_ms,monotonic_ns,event_type,
semantics,reported_delay_min_s,reported_delay_max_s. Debe preservar hora de
pulsacion sin restarle retraso; el intervalo inferido es un derivado versionado.
null en JSON y celda vacia en CSV; cero es dato, no ausencia. Enteros de reloj
deben parsearse sin pasar por float; no transferir nanosegundos como Number JS.

checksums.json lista ruta relativa, bytes, SHA-256 de cada archivo excepto si
mismo. Primero escribir en temporal, cerrar handles, verificar contenido y
publicar el ZIP. Fallo conserva estado INCOMPLETE. Ni este escritor ni su lector
V1 estan implementados. Evitar adaptar RAW existente para aparentar ese contrato.

Validacion V1: version mayor desconocida -> rechazo; columnas nuevas compatibles
se conservan o ignoran con aviso; campos obligatorios ausentes -> rechazo. Limites
propuestos por paquete: 1 GiB descomprimido, 100 archivos y razon de compresion
200:1; revisar con captura representativa antes de aprobar. No implementados en
loader actual. No extraer rutas peligrosas ni cargar archivos sin limite en API.

## 4. Politica de fallos y salida

| Situacion | Tratamiento objetivo | Estado actual |
|---|---|---|
| Pareja CSV/ZIP ambigua | Detener y pedir asociacion | Manifiesto explicito actual |
| Epoch anotacion invalido o inicio/fin inconsistente | Rechazar sesion etiquetada | read_annotations implementado |
| Duplicados/gaps | Auditar RAW; derivado ordenado sin ocultar conteos | Piloto cuenta RAW; V0 calidad posterior a normalizacion |
| Falta gyro/total | V0 puede continuar; piloto con ese esquema no | Requisito del piloto implementado |
| GPS lejano >2 s | No asignar coordenadas | associate_gps implementado |
| Quality INVALID | Bloquear uso cientifico y registrar motivo | Gate general V0 pendiente |
| Cambio de montaje | Nueva condicion, no mezclar sin documentar | Conocido por declaracion; no medido automaticamente |
| Export parcial/duplicado | Estado explicito/idempotencia por hash | Catalogo transaccional pendiente |

Resultados piloto: dataset.csv, annotations.csv, candidates.csv, metrics.csv,
corridor_metrics.csv, predictions.csv, errors.csv, audit.json, provenance.json
y revision_senales.csv. Provenance contiene fuentes y hashes, configuracion,
codigo y versiones. No mezclar IDs de muestras entre ejecuciones sin run_id.
Los errores de ventanas no equivalen a FP/km del detector continuo.

Criterios de cierre: ejemplo V1 validado, pruebas de reloj (salto, zona, reinicio,
unidades), fallo de escritura, paquete parcial y compatibilidad legacy. Hoy hay
tests de epoch/gaps y campana legacy reproducida; la bateria V1 queda pendiente.

## 5. Incrementos Android implementados posteriormente

El 27/09 se implemento [capture-preview-2](IMPLEMENTACION_ANDROID_A3.md), con seis
CSV planos, metadatos y anotaciones legacy. Conserva tiempos nativos, cuaterniones
y campos GPS opcionales. Sustituye imu-preview-1 para nuevas capturas, sin modificar
los archivos historicos. El detalle del esquema real esta en el documento enlazado.

Este perfil de desarrollo no cierra el V1 propuesto de la seccion 3: faltan hashes,
identificadores y metadatos completos, adaptador Python por version y aceptacion
telefono-PC. No enviar estos ZIP al lector Sensor Logger suponiendo equivalencia.

La [revision de cierre](REVISION_CIERRE_ETAPA2.md) reprodujo aceptacion parcial
incorrecta: aceleracion lineal ignorada como duplicado, epoch reconstruido en 1970
y precision/velocidad GPS sin mapeo a columnas esperadas. Hasta corregirlo, este
lector no sirve para validar cientificamente la exportacion de captura propia.
