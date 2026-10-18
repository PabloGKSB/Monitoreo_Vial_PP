# Contrato de carga e inspeccion local

Version HTTP/resultados: **inspection-api-1**, implementacion 0.1.0.
Fecha: 2026-10-09. Subtareas: E3-01/E3-04. Padres: T-07/T-17, HU-07/HU-21.

## Alcance de este incremento

La API reutiliza load_trip, assess_trip, prepare_gps y route_summary. Acepta ZIP
de Sensor Logger y capture-preview-2 para inspeccionar trayectoria, calidad y
marcas disponibles. No ejecuta un clasificador ni cambia el modo de analisis del
V0 existente. `detection.status=NOT_EVALUATED` y `event_count=null` expresan que
no se evaluaron detecciones: no se interpreta como cero baches.

Incremento 10/10: se agrega processing_policy con version quality-policy-1,
motivos y deteccion permitida o denegada. Resultados de inspeccion anteriores
sin ese campo se muestran con politica desconocida y denegacion conservadora.
El [modo central](INTEGRACION_SUPABASE.md) agrega autenticacion e historial;
este contrato describe la demo local sin cuentas, no acceso publico autorizado.

No hay cuentas ni autorizacion por propietario. La configuracion de arranque
se limita a 127.0.0.1 y un proceso. Esta version es una demostracion local previa
a E3-05/06/07/08; no es el servicio multiusuario alojado en Railway.

## Perfiles de entrada y tiempo

| Perfil | Identificacion | Archivos y semantica |
|---|---|---|
| capture-preview-2 | metadata.json con schema_version exacta | Seis flujos CSV posibles y anotaciones declaradas. Lineal y total permanecen separadas; minimo para inspeccion: aceleracion y GPS. |
| Sensor Logger legado | Sin manifest nativo ni linear_acceleration.csv que implique captura propia | CSV reconocidos por loader.py, opcionales y nombres tolerados por ese lector. Minimo: acelerometro y GPS. |
| Otro nativo | Manifest desconocido, incoherente o ausente en captura propia | Trabajo FAILED/INVALID_TRIP; no se reconvierte silenciosamente en legado. |

El [adaptador nativo](../etapa2/ADAPTADOR_NATIVO_V0.md) es la referencia de campos
que la APK produce. inspection-api-1 versiona la respuesta de inspeccion, no
promueve capture-preview-2 al contrato futuro V1.

- Anclas metadata: origin_monotonic_ns, origin_epoch_ms,
  annotation_origin_monotonic_ms y annotations_file.
- CSV inerciales: sensor_timestamp_ns entero, epoch_ms_derived,
  seconds_elapsed, x/y/z; rotation_vector usa qx/qy/qz/qw.
- GPS: mismos campos de tiempo, latitude/longitude; speed_mps y
  horizontal_accuracy_m opcionales. Se conserva location_epoch_ms en el lector.
- Marcas: trip_id, epoch_ms, elapsed_ms, event_type; timestamp textual opcional.
- Coordenadas en grados, aceleracion m/s2, giroscopio rad/s, gravedad m/s2,
  velocidad GPS m/s; respuesta de velocidad en km/h. Las unidades de magnitudes
  son las declaradas por el perfil de captura, no una calibracion demostrada.
- El timestamp nativo se reconstruye desde epoch y diferencias monotonas. Las
  respuestas JSON usan UTC. No se restan 2-3 s a las marcas en esta API; ese
  desplazamiento solo corresponde a protocolos experimentales declarados.

Antes de cerrar T-07 falta una prueba fisica de marca/deshacer/exportacion y
resolver explicitamente las diferencias del esquema de entrega con V1.

## Endpoints

| Metodo y ruta | Respuesta | Uso |
|---|---|---|
| GET /health | 200 | Disponibilidad y limites locales. |
| POST /v1/jobs | 202 + Location | Campo multipart `file` con un .zip. Identificador UUID, SHA-256, tamano y estado inicial. |
| GET /v1/jobs/{job_id} | 200 | QUEUED, PROCESSING, COMPLETED o FAILED y error si corresponde. |
| GET /v1/jobs/{job_id}/result | 200 o 409 | Resultado disponible solo en COMPLETED. |
| GET /v1/jobs/{job_id}/map | 200 HTML o 409 | Mapa Folium del mismo resultado y sus tramos GPS. |
| GET /openapi.json | 200 | Contrato OpenAPI generado por FastAPI, disponible tambien en /docs. |

Los identificadores no son permisos de acceso. No existe un endpoint de listado
global ni un mapa publico de irregularidades en este incremento.

Estados: QUEUED -> PROCESSING -> COMPLETED/FAILED. 202 significa aceptacion de la
carga estructural, no confirmacion de validez semantica de los sensores. Un ZIP
correcto como contenedor pero con perfil futuro puede dar 202 y luego FAILED.
COMPLETED significa inspeccion terminada, incluso si `quality.overall_status`
es INVALID; el resultado permite revisar el problema sin producir detecciones.

## Resultado

| Campo | Significado |
|---|---|
| contract_version, analysis_mode | inspection-api-1, inspection. |
| capture_profile, trip_id | Perfil y ID interno del recorrido; job_id identifica la carga aparte. |
| summary | Duracion, observed_distance_km, mean_fix_speed_kmh, cantidad de fijaciones/tramos, calidad, estado y descartes declarados. |
| quality | Reporte temporal/GPS completo y sus advertencias. |
| warnings, sensors | Advertencias del lector, conteos y nombres de entradas ZIP. |
| trajectory | GeoJSON FeatureCollection; coordenadas [longitud, latitud]. LineString por tramo, Point si hay una fijacion aislada. |
| gps_fixes | Tiempos, coordenadas, tramos, precision disponible, velocidad y distancia acumulada. |
| annotations | Referencias manuales en su tiempo original; no detecciones automaticas. |
| detection | NOT_EVALUATED, event_count null. |

Huecos GPS mayores de 2 s separan tramos y no suman distancia entre extremos,
igual que en el V0. La distancia es observada y la velocidad media es de las
fijaciones conservadas, no distancia real total o velocidad media corregida por
tiempo. No se rellenan huecos. Valores numericos opcionales ausentes se serializan
como null, no NaN/Infinity. La API no devuelve las muestras inerciales completas.

El mapa conserva inicio/fin y los tramos observados. Las marcas estan disponibles
en JSON; no se georreferencian ni publican como irregularidades confirmadas.

## Errores y limites de esta prueba

| Codigo | Caso |
|---|---|
| 404 | job_id valido pero inexistente. |
| 409 | Resultado aun pendiente o trabajo fallido; incluye estado/error. |
| 413 | Carga >64 MiB, total descomprimido >256 MiB, compresion excesiva o manifest >1 MiB. |
| 415 | Extension distinta de .zip. MIME no se considera prueba suficiente de formato. |
| 422 | ZIP invalido/vacio, mas de 1.000 entradas, rutas inseguras/duplicadas, cifrado/enlaces o UUID invalido. |
| 429 | Capacidad de cuatro trabajos activos/pendientes alcanzada; Retry-After: 5. |

Limites configurables mediante create_app para pruebas; /health publica los
valores efectivos. Los bytes se leen por bloques y se calcula SHA-256. Las
entradas se leen dentro del ZIP sin extraerlas. Cargas rechazadas no dejan
carpetas aceptadas. La comprobacion de CRC/CSV ocurre al leer los flujos.

La carga multipart ya se ha recibido/spooled al entrar al endpoint: estos
limites no sustituyen un limite de cuerpo HTTP en el alojamiento. El lector
todavia usa pandas en memoria. Antes de alojar: medir recursos, autenticar,
limitar cuerpos a nivel de servidor y establecer retencion/cuotas.

## Persistencia local y ejecucion

`.api_local/{job_id}/` conserva input.zip, job.json y result.json. Se escribe JSON
mediante reemplazo de archivo temporal y bloqueo local entre lecturas/escrituras
de estado, necesario para reemplazo concurrente en Windows. `.api_local/` se excluye de Git y no se
sirve como carpeta publica. Variable opcional VIAL_API_STORAGE cambia su ruta.

Un trabajador en el proceso inspecciona un ZIP a la vez. Al reiniciar, trabajos
QUEUED/PROCESSING anteriores pasan a FAILED/PROCESS_INTERRUPTED y requieren una
nueva carga. Los completados pueden consultarse despues del reinicio. No hay
cola distribuida, reintento automatico ni idempotencia: subir el mismo ZIP crea
otro job_id con el mismo hash. No ejecutar varios procesos sobre la misma carpeta.
La retencion y limpieza de trabajos completados son manuales en esta prueba.

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-api.txt
.\.venv\Scripts\python.exe run_api.py
```

Abrir http://127.0.0.1:8000/docs. Si el puerto esta ocupado:

```powershell
.\.venv\Scripts\python.exe run_api.py --port 8001
```

En /docs ejecutar POST /v1/jobs con un ZIP, copiar job_id y consultar estado,
resultado y `/v1/jobs/{job_id}/map`. Las librerias/cartografia del mapa y Swagger
usan recursos externos; cargar el HTML no garantiza disponibilidad offline.

## Referencias de implementacion

[UploadFile](https://fastapi.tiangolo.com/tutorial/request-files/) y
[lifespan](https://fastapi.tiangolo.com/advanced/events/) siguen las interfaces
documentadas de FastAPI. La [guia de tareas](https://fastapi.tiangolo.com/tutorial/background-tasks/)
motiva separar el procesamiento pesado cuando se prepare el despliegue durable.
Esta version usa un trabajador local acotado para obtener evidencia inicial.
