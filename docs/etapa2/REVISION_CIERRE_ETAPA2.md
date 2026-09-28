# Revision de cierre de diseno y backlog

Revision: 2026-09-27. No es aprobacion del profesor ni cierre de Etapa 2.
Alcance: contrastar informe original, documentos, codigo y evidencia existente.
No se implementan funcionalidades ni se modifican RAW, etiquetas o modelos.

## 1. Hallazgos prioritarios

### R-01. Integracion Android-PC no cerrada (prioridad alta)

El informe original exige en HU-07 que el pipeline PC lea la salida generada
(p. 33). La captura propia exporta capture-preview-2; el lector Python sigue
orientado a Sensor Logger. No basta con que un ZIP se abra o se pueda leer con pandas.

Prueba de lectura efectuada sobre el ZIP real de 20:40:12, sin ejecutar deteccion:

```text
load_trip(...) devuelve accelerometer, gps, gravity, gyroscope, orientation
Duplicate accelerometer ignored: linear_acceleration.csv
Unrecognized CSV ignored: ..._anotaciones.csv
primer timestamp de accelerometer: 1970-01-01 00:00:00.067090385+00:00
```

La velocidad queda en `speedmps`, no `speed`; la precision GPS en
`horizontalaccuracym`, no `horizontal_accuracy`. metadata.json no se interpreta
como contrato de captura propia. El lector conserva el accelerometer total y
descarta el lineal como duplicado: que V0 tenga una heuristica de compensacion de
gravedad no convierte eso en soporte explicito y trazable de ambos flujos.

Referencias: [loader](../../src/loader.py), [reloj](../../src/utils.py),
[calidad](../../src/quality.py), [asociacion GPS](../../src/gps.py).
Consecuencia: no usar este camino para resultados cientificos de captura propia.
Es una brecha comprobada de HU07/D03/D04/D06, no una falta cosmetica de documentacion.

Accion siguiente propuesta: discriminacion por schema_version, adaptador explicito
y pruebas de regresion; mientras no exista, rechazar claramente este perfil en
el lector legacy. Cierre: el mismo ZIP conserva epoch, seis flujos, unidades,
precision/velocidad y anotaciones; formatos desconocidos no se aceptan por accidente.

### R-02. Diseno describe una arquitectura anterior (prioridad alta)

DISENO_TECNICO y PROTOCOLO todavia decian que no habia captura propia ni build nuevo.
Se corrigieron en esta revision sus descripciones vigentes. Los diagramas HTML
existentes siguen sin ser evidencia suficiente de Android A3/B1 y piloto actual.
D01 no puede cerrarse solo con diagramas de V0 o de una propuesta futura.

### R-03. No hay linea base de cierre del diseno aceptada (prioridad alta)

Las 26 HU y 18 tareas originales se contrastaron con pp. 31-35 del informe.
D01-D10 son subtareas propuestas posteriormente; no constituyen por si solas un
denominador aprobado. No calcular 100 % eliminando pendientes ni confundir pruebas
pasadas con aprobacion del diseno. Mantener cada D con criterio y revision fechada.

### R-04. Evidencia fisica positiva, pero acotada (prioridad media)

El ZIP real demuestra cinco sensores, GPS, inicio/fin y exportacion en una sesion
de 88.833 s. La auditoria independiente confirma conteos y relojes. No contiene
marcas manuales; no demuestra pantalla apagada, recuperacion tras muerte del
proceso, bateria, repetibilidad ni deteccion de baches. GPS presento demora inicial,
precision pobre al principio y un intervalo de 5 s.

Evidencia: [revision de captura](REVISION_CAPTURA_PROPIA_20260927_204012.md).
Actualizar la evidencia del backlog no equivale a cerrar la aceptacion completa.

### R-05. Version de entrega y trazabilidad incompletas (prioridad alta)

Python tiene Git, pero `docs/`, `src/pilot/`, `configs/`, pruebas y lanzador figuran
sin seguimiento, ademas de modificaciones existentes. Android no tiene `.git`.
Los parches y backups son utiles, pero no sustituyen commits ni una version de
entrega reproducible. No se realizaron commits, limpieza o cambios de repositorio.
Revisar contenido y privacidad antes de versionar; no subir ubicaciones RAW.

## 2. Contraste con aceptacion original

I/P/N del backlog describen presencia de implementacion, NO aprobacion de una HU.
No se anaden retroactivamente requisitos mas fuertes como condicion de su historia.

| HU / fuente | Comprobado | Limite para el cierre |
|---|---|---|
| HU02, p. 32 | Inicio, ID local, reloj, servicio, drenado y exportacion; ZIP real con INICIO/FIN. | Revisar unicidad local/colisiones y aceptacion del flujo en el equipo. Recuperacion pertenece al diseno de persistencia, no es criterio explicito adicional de HU02. |
| HU03, p. 33 | Timestamps, XYZ/cuaternion, archivos por tipo, metadatos y conteos; cinco sensores reales. | Declarar alcance del contador de descartes y ensayos de continuidad/carga; no prometer detectar toda perdida del SO. |
| HU04, p. 33 | Latitud/longitud, precision, timestamp y velocidad en la sesion real. | Aceptacion de permisos/ausencia de fijacion y continuidad; no confundir precision reportada con error espacial medido. |
| HU06, p. 31 / T05 p. 34 | Escritura local buffered y archivos recuperables desde historial. | Room/DAOs no existen: desviacion de tarea tecnica pendiente de aceptar, no ausencia total de persistencia. |
| HU07, p. 33 | Exportacion RAW y metadata demostrada; pertenencia a sesion por paquete y nombre del CSV de marcas. | R-01; explicitar ID de sesion/relacion de archivos en contrato. No sustituir lectura de pipeline por inspeccion ad hoc. |
| HU09, p. 31 | Codigo de marcas, tests de CSV y campana legacy anotada. | Nueva captura sin marcas; falta prueba integrada de pulsacion/deshacer/exportacion. |
| HU10, p. 33 | Metricas temporales en Android y QualityReport en Python. | No hay gate general que detenga TripAnalyzer al obtener INVALID; la lectura limpia duplicados antes de calidad. Auditar RAW antes de normalizar. |
| HU14, p. 33 | Baseline V0 existente y configuracion. | Validar reproducibilidad sobre formato admitido; no afirmar deteccion evaluada en APK propia. |
| HU17, p. 34 | Piloto exploratorio con grupos, no reparto aleatorio de ventanas. | Etiquetas/referencias provisionales y muestra limitada; no implica generalizacion. |
| HU19, p. 34 | Mapa V0, no mapa Android. | Evidencia visual y asociaciones validas; evitar atribuirlo a la APK. |

## 3. Revision D01-D10

| D | Resultado de esta revision | Trabajo concreto para cerrar diseno |
|---|---|---|
| D01 | Descripcion vigente corregida; diagrama pendiente. | Componentes y flujo actual con adaptador pendiente visible, separados del destino futuro. |
| D02 | Modelo logico existente; cardinalidades especificadas, sin DDL/DAOs. | Revisar variantes XYZ/cuaternion, identidad de sesion y ejemplo de integridad; decidir destino de persistencia. |
| D03 | Perfil real y ZIP de ejemplo auditados; no soporte PC. | Congelar alcance del perfil para entrega, mapeo al modelo PC, errores/versiones y pruebas del contrato. |
| D04 | Anclas comprobadas en ZIP; lector legacy produce epoch incorrecto. | Especificar conversion por perfil, salto de reloj/reinicio y pruebas; no interpretar monotono como epoch. |
| D05 | Servicio, permisos y drenado implementados; historial no recupera captura activa. | Revisar maquina actual y politica de sesion interrumpida; distinguir propuesta Room de archivos existentes. |
| D06 | Calidad y pipelines descritos; politica no aplicada de extremo a extremo. | Fijar gates, tratamiento de precision GPS y casos INVALID, versionados antes de evaluar. |
| D07 | Protocolo actualizado con captura propia; ficha sigue plantilla. | Completar datos de vehiculo/montaje/version y revisar incertidumbre de marcas con Pablo. |
| D08 | Hipotesis/grupos definidos; matching continuo futuro. | Revisar tolerancias/matching/denominadores y separacion desarrollo-test; no exige ejecutar ML movil. |
| D09 | Backend como extension respaldado por p. 29; OE5 sigue vigente. | Acordar compromiso de diseno para entrega; OpenAPI y diseno de acceso siguen abiertos si forman parte de ese compromiso. |
| D10 | Registro de brechas y decisiones actualizado. | Aceptar decisiones, consolidar evidencias, Git y politica de datos; revision final de trazabilidad. |

Ninguna D se declara aprobada por este documento. Tampoco se afirma que el avance
real sea cero: hay diseno y evidencia, pero el denominador y la aceptacion no estan
cerrados. Aceptacion de diseno, implementacion y ensayo fisico son registros distintos.

## 4. Decisiones para revisar con Pablo

1. Mantener archivos buffered como persistencia inicial y Room como trabajo posterior
   explicitamente pendiente de T05, en lugar de afirmar que se implemento Room.
2. Documentar LocationManager/GPS_PROVIDER como alternativa actual a FusedLocationProviderClient,
   con sus consecuencias de recepcion y sin equivalencia experimental presupuesta.
3. Mantener capture-preview-2 como perfil de desarrollo, o promover un contrato de
   entrega versionado tras resolver R-01. No renombrarlo V1 sin satisfacer sus reglas.
4. Priorizar el nucleo y documentar API/PostGIS como extensiones segun p. 29; no
   borrar OE5 ni presentar esa priorizacion como una autorizacion nueva del profesor.

El 7.0 y el comentario positivo recibido no contienen correcciones especificas.
Estos hallazgos son revision interna; no atribuirlos al profesor. Falta conservar
correo/fecha como evidencia del criterio de retroalimentacion, segun exigencia de entrega.

## 5. Orden de trabajo para la entrega del 2 de octubre

| Orden | Entregable | Criterio observable |
|---|---|---|
| 1 | Contrato y adaptador Android-PC / rechazo seguro legacy | Pruebas con ZIP propio, epoch correcto, todos los flujos y regresion Sensor Logger. |
| 2 | Diseno actualizado y diagramas | D01-D06 revisables contra archivos reales, sin flechas de integracion inexistentes. |
| 3 | Protocolo y prueba minima pendiente | Una marca manual, exportacion, reapertura, permisos/rotacion y pantalla apagada con resultados documentados. |
| 4 | Backlog y decisiones aceptadas | Cada D tiene responsable, evidencia, estado y pendientes; sin porcentajes inflados. |
| 5 | Informe, evidencias y Git | Cuatro criterios de rubrica trazados, commits descriptivos y version identificable sin RAW privado. |

No se priorizan nuevas pantallas, detector movil ni backend completo durante este cierre.
La integracion R-01 es cumplir un contrato ya comprometido, no ampliar funcionalidades.

## 6. Verificaciones de esta revision

- Informe Etapa 1, pp. 29-35, consultado directamente del PDF de Downloads.
- 26 HU y 18 T conservadas, con mismas prioridades/puntos del inventario original.
- `python run_tests.py`: 22 pruebas Python aprobadas durante esta revision.
- Reportes XML Android inspeccionados: 27 pruebas JVM aprobadas de la ejecucion
  anterior; no se reejecutaron Android ni pruebas fisicas en esta revision.
- Prueba de lectura del ZIP propio reprodujo R-01; no se ejecuto entrenamiento
  ni se generaron resultados de deteccion con esa lectura incompatible.
- Git inspeccionado sin modificar cambios previos ni crear commits.

Conclusion: existe implementacion inicial demostrable, pero la entrega no se cierra
solo escribiendo el informe. La prioridad tecnica es R-01; en paralelo deben
cerrarse descripcion/diagramas, decisiones, protocolo, backlog y versionado.
