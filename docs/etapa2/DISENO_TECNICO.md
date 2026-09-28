# Diseno tecnico de Etapa 2

Estado: revision v0.2 de coherencia, 2026-09-27; pendiente de aceptacion.
Se separan implementacion vigente y modelo objetivo. Ver [revision de cierre](REVISION_CIERRE_ETAPA2.md).
Trazabilidad: OE1-OE6; HU-01 a HU-26 segun [backlog](BACKLOG.md).
Formatos y unidades en [contrato](CONTRATO_DATOS.md).

## 1. Limites y responsabilidades

| Componente | Situacion observada | Responsabilidad objetivo |
|---|---|---|
| Sensor Logger | Fuente externa de ZIP de sensores. | Adaptador de legado; conservar trazas originales. |
| AnotadorVial / adquisicion propia | Una misma app Kotlin en AndroidStudioProjects: UI B1, servicio A3, cinco sensores, GPS, CSV/JSON/ZIP e historial. Build, pruebas JVM y captura real auditada. | Captura offline y marcas independientes del detector. |
| Adaptador captura propia a Python | Pendiente; lector legacy acepta parcialmente capture-preview-2 con semantica incorrecta. | Validacion por version, relojes, unidades y flujos sin romper legado. |
| TripAnalyzer V0 | Implementado en src/analyzer.py. | Analisis continuo exploratorio, eventos candidatos y segmentos. |
| Piloto etiquetado | Implementado en src/pilot/. | Comparar ventanas asistidas por etiquetas; no deteccion continua validada. |
| Streamlit | app.py implementado. | Inspeccion y mapa V0, no entrenamiento piloto integrado. |
| FastAPI/PostGIS/web final | Propuesto, no implementado aqui. | Consultas, historial y persistencia central posterior. |

El nucleo cientifico debe funcionar offline sin FastAPI ni PostGIS. No se borra
OE5: su calendarizacion se revisa explicitamente con el profesor. Room y recuperacion
de captura activa siguen pendientes; el servicio y capture-preview-2 ya existen.
La cola actual es local y acotada (4096 muestras compartidas), no distribuida.
La captura propia no esta integrada al nucleo Python: no dibujar esa conexion como
implementada. Sensor Logger sigue siendo el formato de los experimentos previos.

## 2. Modelo logico propuesto

Notacion relacional: PK clave primaria, FK referencia. UUID como identificador
objetivo; los identificadores de nombres de archivos actuales se conservan como
legacy_id, no se asumen UUID ni nombres unicos globales. Coordenadas WGS84.

| Entidad | Clave y campos principales | Reglas |
|---|---|---|
| Corridor | corridor_id PK, nombre_controlado | Unidad geografica de agrupacion, no identidad de defecto. |
| Session | session_id PK, corridor_id FK, direction, pass_index, device_id, vehicle_id, start_epoch_ms, clock_anchor_ns, capture_state, mount_state, protocol_version | Una pasada/sentido; identidad nueva aunque se repita ruta. Final >= inicio. Datos desconocidos null. |
| SensorStream | stream_id PK, session_id FK, sensor_type, units, axis_frame, requested_hz, sensor_properties | Unidades y marco explicitos; disponibilidad no implica captura valida. |
| Sample | stream_id FK, sequence_no, raw_time, monotonic_ns, x/y/z, accuracy | PK compuesta (stream_id, sequence_no); mantener duplicados temporales para auditoria. No indexar por timestamp unico. |
| RotationSample (variante propuesta) | Misma clave Sample, qx/qy/qz/qw nullable, heading_accuracy_rad nullable, value_count, sensor_accuracy | XYZ solo no representa un cuaternion; conservar opcionales sin inventarlos. |
| LocationFix | session_id FK, sequence_no, epoch_ms, monotonic_ns, lat/lon, speed_m_s, horizontal_accuracy_m | PK (session_id, sequence_no); precision desconocida null; geometria derivada, no correccion de RAW. |
| RawArtifact | artifact_id PK, session_id FK, role, relative_path, sha256, bytes, format_version | Hash de bytes; conservar nombre y origen. Unicidad (session_id, role, sha256); duplicado no equivale a sesion nueva. |
| Annotation | annotation_id PK, session_id FK, raw_row, button_epoch_ms, elapsed_ms, event_type, operator_id, semantics | Pulsacion distinta del instante del impacto; el RAW nunca se reescribe por revisar etiquetas. |
| LabelRevision | revision_id PK, annotation_id FK nullable, session_id FK, interval_start/end, class_label, confidence, evidence_ref, reviewer, reason, supersedes_id | Permite NORMAL revisado sin marca; intervalo dentro de sesion; historial append-only. |
| AnalysisRun | run_id PK, pipeline_kind, code_version/hash, config_json/hash, created_utc, state | No sobrescribir ejecucion. Version separada para V0 y piloto. |
| RunInput | run_id FK, artifact_id FK | Relacion N:M; cada entrada queda fijada por hash. |
| FeatureWindow | window_id PK, run_id FK, session_id FK, start/end, mode, features, label_revision_id nullable | Clave unica (run_id, session_id, mode, start, end); evita mezclar modalidades. |
| DetectedEvent | event_id PK, run_id FK, session_id FK, start/peak/end, score, predicted_class nullable, gps_fix_id nullable | Candidato no igual a Annotation ni a defecto confirmado; sin GPS queda sin geometria. |
| Segment | segment_id PK, run_id FK, session_id FK, from_m/to_m, summary, geometry | Longitud configurada; indice relativo no escala normativa. |
| EvaluationFold | fold_id PK, run_id FK, group_policy, train/test_ids, purge_radius_m, label_version, confusion, status | Train y test disjuntos segun hipotesis; sin clases suficientes no inventar metricas. |

Cardinalidades: Corridor 1:N Session; Session 1:N streams, fixes, artefactos y
anotaciones; Annotation 1:N revisiones; Run N:M artefactos; Run 1:N ventanas,
eventos, segmentos y folds. Session 1:N LabelRevision cubre intervalos negativos.
El GPS de un evento referencia una fijacion de la MISMA sesion; la ventana y su
revision tambien deben pertenecer a esa sesion. Un trigger/validacion de servicio
futuro debe impedir referencias cruzadas incoherentes.

Destino Room: Session, SensorStream, Sample, LocationFix, Annotation y exportacion.
Destino central: metadatos, artefactos, resultados y revisiones; RAW en archivos
inmutables referenciados, sin exigir copiar cada muestra a PostGIS. Los tipos
geoespaciales propuestos son Point/LineString SRID 4326, distancias en metros
mediante conversion apropiada; no medir metros directamente en grados.
Indices objetivo: session_id+tiempo, run_id, sha256 y espacial de geometria.
Migraciones numeradas; importacion idempotente por hash, sin fusion automatica
de anotaciones de ida y vuelta. DDL, DAOs y migraciones ejecutables pendientes.

## 3. Flujos y estados

### F-01 Captura legacy de la campana 25/09 (RF01-12; RE01-08)

1. Operador documenta montaje; inicia Sensor Logger y luego Anotador.
2. Ambas apps tienen sesiones independientes. La marca MONITOREO_INICIO no
   equivale al inicio de Sensor Logger.
3. Acompanante marca despues del episodio; el CSV conserva la hora de pulsacion.
4. Finaliza anotador y captura; exporta ZIP y CSV; asocia explicitamente la pareja.
5. PC calcula hashes y audita sensores/relojes antes de construir ventanas.

### F-02 Captura propia objetivo (HU02-07; T01-07)

| Estado | Transicion/condicion | Accion y salida |
|---|---|---|
| IDLE | Iniciar con permisos y sensores minimos | Crear UUID, anclas de reloj y metadatos; PREPARING. |
| PREPARING | Persistencia y servicio disponibles | Registrar listeners; RECORDING. Fallo -> ERROR, sin fingir captura. |
| RECORDING | Muestra o marca | Buffer acotado y escritura por lotes; registrar perdidas/overflow. |
| RECORDING | Finalizar | Detener listeners, drenar buffers; FINALIZING. |
| FINALIZING | Escritura confirmada | Cerrar sesion; COMPLETED. Fallo -> ERROR con datos parciales preservados. |
| COMPLETED | Exportar | Construir temporal, comprobar filas/hash y publicar ZIP; EXPORTED. |
| ERROR | Recuperacion explicita | Conservar sesion INCOMPLETE, exportar parcial con aviso; nueva captura usa otro ID. |

No se propone pausa en v1: finalizar y crear sesion nueva evita continuidad falsa.
Un reinicio no reanuda implicitamente el reloj monotono de una sesion anterior.
Esta tabla describe el objetivo completo, no todos los estados persistidos hoy.
En A3 hay listeners, cola, drenado y cierre COMPLETED/INCOMPLETE en JSON,
pero no UUID, Room, checksums ni EXPORTED transaccional. El ID actual es nombre/fecha.

### F-02a Captura propia vigente A3/B1

1. MonitoringApp comprueba sensores y permiso preciso GPS; puede continuar sin GPS
   explicitamente. La burbuja remite a UI para iniciar con GPS.
2. iniciarNuevaSesion crea CSV de marcas e INICIO y solicita RecordingService.
3. Servicio registra sensores y LocationManager con tipos foreground apropiados.
   Anotaciones y muestras tienen anclas monotona/civil relacionadas.
4. Callbacks copian muestras a cola; escritor dedicado vacia seis CSV. UI observa
   conteos/Hz/estado; las marcas conservan E/S sincrona de baja frecuencia.
5. Finalizar escribe FIN, detiene listeners y drena/sincroniza archivos y metadata.
   Exportacion se habilita despues del cierre; sin fijaciones no se inventa GPS.
6. Historial lee archivos. Una muerte del proceso puede dejar RECORDING; no se
   reanuda ni se reconstruye automaticamente la captura activa.
7. ImuArchive exporta ZIP. Adaptador Python propio PENDIENTE: la inspeccion manual
   del ZIP no demuestra integracion con el pipeline.

### F-03 Importacion y analisis (RF13-22; RNF05-07)

1. Seleccionar fuentes y modo; rechazar parejas ambiguas. Catalogar RAW y hashes.
2. Validar contrato, unidades y relojes; auditar antes de ordenar/deduplicar.
3. Evaluar calidad: ACCEPT, REVIEW o REJECT segun reglas del protocolo.
4. Ejecutar V0 sin marcas para proponer eventos, O piloto con marcas para
   comparar ventanas. Nunca mezclar los resultados como si fueran el mismo detector.
5. Asociar GPS con tolerancia; fuera de ella mantener null y motivo.
6. Exportar resultado y procedencia en carpeta nueva. Error conserva diagnostico;
   RUNNING -> SUCCEEDED solo despues de escribir todos los artefactos.

Actual: el piloto tiene carpetas unicas; V0 sobreescribe nombres al exportar.
TripAnalyzer calcula QualityReport pero no bloquea explicitamente INVALID.
El loader ordena/deduplica; el piloto reaudita RAW. La maquina de ejecucion
PENDING/RUNNING/SUCCEEDED/FAILED persistida es objetivo, no codigo existente.

### F-04 Revision/evaluacion (RF21, RF29-30; T12-15)

RAW + evidencia externa -> anotacion -> revision versionada -> dataset fijado
-> separacion por grupo -> ajustes solo en train -> predicciones de test -> informe.
Las revisiones ambiguas no se fuerzan a BACHE/NORMAL. En evaluacion continua
futura, matching uno-a-uno de deteccion y referencia dentro de tolerancias
prefijadas; unmatched detection = FP, unmatched reference = FN. Resolver
empates por distancia temporal y luego ID estable. Este matching no esta en
el piloto de ventanas y el comparador V0 permite reutilizacion: T12 sigue abierto.

## 4. Decisiones y consecuencias

| ID | Decision propuesta o conservada | Motivo / limite | Requisitos |
|---|---|---|---|
| ADR01 | Adaptadores separados legado y captura propia | No romper campaña existente; diseno de v1 no implica compatibilidad actual. | RF12, RNF06 |
| ADR02 | Epoch para alinear apps, monotono para intervalos | Evitar desfase de texto local; detectar saltos del reloj civil. | RF16, RD02-03 |
| ADR03 | Anotacion retrospectiva y revision distinta de deteccion | No entrenar contra la propia salida como unica verdad. | RE06/08, HU16 |
| ADR04 | V0 y piloto como pipelines separados | Umbral supervisado no reemplaza detector robusto V0. | HU14/17, RNF10 |
| ADR05 | Ida/vuelta agrupadas por corredor para generalizacion | Mismo lugar no independiente; repetibilidad es otra pregunta. | RF30, RE09-10 |
| ADR06 | RAW privado, derivados trazables y ejecuciones inmutables | Reproducibilidad y minimizacion de ubicaciones compartidas. | RNF05-07/12-13 |
| ADR07 | Captura offline primero, servicios centrales despues | Acotar complejidad; mantener OE5 visible, no eliminarlo. | RF11/24/25, R13 |
| ADR08 | CSV buffered inicial; Room pendiente | Implementado; aceptacion de desviacion T05 pendiente. Historial no es recuperacion transaccional. | HU06, T05/06 |
| ADR09 | LocationManager/GPS_PROVIDER en lugar de Fused | Sin dependencia nueva Google Play Services; no demuestra equivalencia con Sensor Logger. Desviacion T03 por aceptar. | HU04, T03 |
| ADR10 | capture-preview-2 distinto de V1 propuesto | Exportacion real; falta adaptador/contrato definitivo. No aceptar perfil por coincidencia de nombres CSV. | HU07, D03/04 |

## 5. Interfaces futuras de consulta (no implementadas)

Consulta local reutiliza TripAnalyzer.analyze/export; el piloto es CLI y no
requiere API. Futuro GET /sessions con paginacion por cursor, filtros fecha UTC,
corridor y dispositivo pseudonimo; GET /sessions/{id}; GET /runs/{id}/events;
GET /runs/{id}/segments. Respuesta JSON con IDs/UTC/null y GeoJSON lon,lat.
Errores: 400 filtro invalido, 404 ID ausente, 403 sin permiso; no exponer rutas
locales o trazas internas. Autenticacion, esquema OpenAPI y trabajos asincronos
de importacion quedan por disenar antes de desplegar: HU20-22 no cerradas.
No publicar servicio abierto ni RAW en GitHub. Copias de evidencia privadas;
periodo de retencion y autorizaciones de acceso por acordar con el participante.

## 6. Verificacion del diseno

| Caso | Resultado esperado | Evidencia actual / pendiente |
|---|---|---|
| Texto metadata difiere 3 h de epoch | Mantener epoch y registrar discrepancia | test_epoch_overrides_formatted_metadata_and_annotation_elapsed |
| Gap de sensor en ventana | Excluir ventana con motivo | test_window_rejects_sensor_gap |
| Ida/vuelta mismo corredor | Nunca repartirlas entre train y test LOCO | test_corridor_folds_keep_outbound_and_return_together |
| Retraso cambia de 1.5 a 2.5 s | Mover solo positivas fijas | test_retroactive_delay_moves_only_fixed_positive_windows |
| App se interrumpe escribiendo | Sesion parcial recuperable, sin perdida silenciosa | Captura propia existe; recuperacion/Room pendientes |
| Archivo hash repetido | Importacion idempotente con vinculo al original | Pendiente catalogo persistente |
| GPS sin fijacion cercana | Coordenadas ausentes, no interpolacion inventada | src/gps.py y tests/test_gps.py |
| Evaluacion continua con dos marcas cercanas | Una deteccion no puede contar dos TP | Pendiente T12 |

Antes de cierre: revisar cardinalidades, ejemplo de exportacion y compatibilidad;
actualizar diagramas de componentes, entidades y secuencia usando convenciones
explicitas. Estas tablas son especificacion de trabajo, no certificacion UML/C4.
