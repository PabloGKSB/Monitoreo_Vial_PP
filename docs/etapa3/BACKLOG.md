# Backlog de Etapa 3

Corte inicial: **2026-10-09**. Entrega: **2026-10-30**.
Actualizacion tecnica: **2026-10-16**.
Responsable: Pablo Javier Gomez Quidel.
Fuente: [inventario de Etapa 2](../etapa2/BACKLOG.md), heredado de Etapa 1.
Estados actuales sustentados por el [registro de evidencias](EVIDENCIAS.md).

## 1. Medicion del 50 % de implementacion

Se usa como referencia el inventario completo **T-01 a T-18**, sin eliminar
Room, FusedLocationProviderClient o la plataforma central. Las 26 HU siguen
visibles en la seccion 3; las diez D describen diseno y no se suman a este indice.
Los puntos de HU se conservan en la fuente original: no se mezclan con el conteo
de tareas solicitado por la rubrica.

| Estado T | Definicion | Cantidad |
|---|---|---:|
| V | Implementacion tecnica verificada para el alcance indicado, con evidencia y criterio operativo satisfecho. | 7 |
| P | Existe trabajo util, pero falta parte del criterio de cierre. | 8 |
| N | Implementacion especifica no evidenciada; puede existir diseno. | 3 |
| Total | Tareas originales, sin ponderar. | 18 |

**Avance tecnico de referencia = 7 / 18 x 100 = 38,9 %.**
**Umbral 50 % = 9 / 18; faltan dos cierres tecnicos adicionales.**

V no significa aceptacion academica ni validacion completa de la HU asociada.
La clasificacion es una revision local actualizada el 16/10, no una fecha retrospectiva de
terminacion. Por ejemplo, T-02 verifica adquisicion SensorManager; la continuidad
operativa se revisa en T-04/T-06 y HU-03. T-13/T-15 verifican herramientas del
piloto; la validez de etiquetas y la generalizacion siguen abiertas en HU-16/17.

Esta interpretacion del denominador debe contrastarse con la retroalimentacion
cuando llegue. Si se acuerdan nuevas tareas de nivel superior, actualizar la
linea base y recalcular todos los cortes; no escoger solo las tareas faciles.
Las E3 de la seccion 4 son subtareas y no se cuentan como tareas originales extra.

## 2. Las 18 tareas y sus criterios

Los criterios siguientes hacen operable el inventario heredado. Las desviaciones
tecnologicas deben registrarse con motivo, fecha y decision antes de cerrar una
tarea cuyo requisito literal no se implemento. No se declara Room o Fused como
realizado por disponer de CSV o LocationManager.

| T | HU | Titulo heredado | Estado | Evidencia | Criterio operativo y pendiente al corte |
|---|---|---|---|---|---|
| T-01 | HU-02 | Proyecto Android y modulos | V | EV-02, EV-11 | Proyecto ejecutable con UI, servicio, captura, reloj, almacenamiento e historial identificables. Evidencia de build historico y fuente actual. Refactorizacion global no es condicion de esta tarea. |
| T-02 | HU-03 | SensorManager | V | EV-02, EV-03, EV-11 | Registro/desregistro y muestras de los cinco flujos inerciales exportadas con timestamps y conteos. Satisfecho para adquisicion; robustez permanece en T-04/T-06. |
| T-03 | HU-04 | FusedLocationProviderClient | N | EV-11 | Implementar el proveedor previsto y probar ausencia/denegacion de GPS, o documentar formalmente la sustitucion y su equivalencia. LocationManager existente no cierra la tarea literal. |
| T-04 | HU-02/03/04 | Foreground Service captura | P | EV-02, EV-03 | Servicio existente. Instrumentar continuidad y demostrar ensayos comparables con pantalla encendida/bloqueada; informar huecos, bateria y errores. |
| T-05 | HU-06 | Room y DAOs | N | EV-01, EV-11 | Entidades, DAOs y migracion ejecutables con pruebas de escritura/consulta/recuperacion, o cambio de alcance documentado. Los CSV no acreditan Room. |
| T-06 | HU-06 | Escritura por lotes | P | EV-02, EV-03, EV-11 | Cola/escritor existentes. Medir carga y descartes, tratar saturacion y cierre; demostrar resultado antes/despues bajo protocolo fijo. Revisar vinculo original con Room. |
| T-07 | HU-07 | Esquema exportacion | P | EV-03, EV-04, EV-12 | Contrato local de perfiles, unidades/relojes y resultados documentado y probado. Falta validar captura propia con marca/deshacer y resolver esquema de entrega preview/V1. |
| T-08 | HU-08 | Montaje y ficha | P | EV-05 | Completar ficha real: vehiculo, dispositivo, montaje, operador, ruta/sentido y versiones. Conservar incertidumbres; ficha utilizable antes de nuevas pasadas. |
| T-09 | HU-09/16 | Anotacion | P | EV-02, EV-05, EV-08 | Marcar dos eventos, deshacer uno, finalizar y leer ZIP en V0; misma sesion, evento conservado y relojes correctos. Probar UI/overlay y errores. Capturas solas no cierran. |
| T-10 | HU-10/11 | Refinar QualityReport | V | EV-13 | Politica INVALID y continuidad compartida, bloqueo antes de procesar, ventanas sin cruzar huecos, eventos separados y segmentos SIN_DATOS probados; V0/exportacion distinguen no evaluado de cero. Verificacion tecnica, no validacion cientifica ni reparacion de captura. |
| T-11 | HU-15 | Sensibilidad V0 | P | EV-05 | Protocolo de variacion de parametros V0, resultados comparables y decision justificada; la prueba del retraso del piloto no cubre toda la tarea. |
| T-12 | HU-23 | Matching uno-a-uno | N | EV-01, EV-05 | Asociar eventos y referencias con tolerancias declaradas; cada referencia/deteccion se usa una vez. Probar duplicados, eventos cercanos y ausencia de coincidencia. |
| T-13 | HU-16 | Dataset features | V | EV-05, EV-06, EV-09 | Construccion reproducible de ventanas/features con fuentes, configuracion y exclusiones registradas. Codigo y ejecuciones evidenciados; calidad cientifica de etiquetas sigue en HU-16. |
| T-14 | HU-17 | Split grupos | V | EV-05, EV-06, EV-09 | Separacion por grupo, ida/vuelta juntas para LOCO local, purga y comprobaciones de no compartir sesiones. Externo por archivo no demuestra independencia geografica. |
| T-15 | HU-17 | Baseline supervisado | V | EV-05, EV-06, EV-09 | Umbral y RF entrenados/evaluados con parametros y resultados reproducibles, sin ajuste en test. Satisfecho como comparacion exploratoria, no detector operativo. |
| T-16 | HU-20 | PostgreSQL/PostGIS | V | EV-14, EV-15, EV-16 | Migraciones, PostGIS, restricciones y rol backend verificados; flujo integrado con dos cuentas Auth reales y ZIP propio completado en ambas, mapas/resultados/originales y aislamiento 404. Verificacion tecnica; no cierra toda la HU. |
| T-17 | HU-21 | FastAPI | P | EV-12, EV-14, EV-15, EV-16 | Autenticacion, renovacion/cierre, repositorio y flujo real probados con dos cuentas; cliente web disponible. Faltan reintentos idempotentes, cola durable y despliegue publicado. |
| T-18 | HU-19/22 | Mapa con endpoints | P | EV-07, EV-12, EV-14, EV-15, EV-16 | Mapa privado e historial por propietario funcionando en cliente web con cuentas reales. Faltan filtros por fecha/tipo/area y publicacion autorizada de observaciones. |

## 3. Inventario completo de historias

I = implementacion evidenciada; P = parcial; N = no evidenciada. Estos estados
conservan el sentido del corte de Etapa 2; I no equivale a HU aceptada. No se usan
para calcular el indicador T de la seccion 1.

| HU | EP | Estado | Situacion actual y siguiente comprobacion |
|---|---|---|---|
| HU-01 | EP-01 | P | Diseno y vista de integracion disponibles; actualizar arquitectura al implementar servicios y registrar ADR. |
| HU-02 | EP-02 | I | Inicio/fin y ZIP reales; verificar ID y flujo integrado de nueva captura. |
| HU-03 | EP-02 | I | Cinco sensores registrados; continuidad presenta huecos y requiere ensayos. |
| HU-04 | EP-02 | I | GPS LocationManager real; probar ausencia/denegacion y conservar diferencias con T-03. |
| HU-05 | EP-02 | P | Conteos/estado y pantallas disponibles; revisar cambios de ciclo de vida y estados de fallo. |
| HU-06 | EP-03 | P | CSV e historial local; recuperacion y desviacion Room pendientes. |
| HU-07 | EP-03 | P | ZIP nativo legible en V0/API y contrato de inspeccion documentado; esquema de entrega y ensayo marca/deshacer pendientes. |
| HU-08 | EP-04 | P | Metadatos parciales; completar ficha de sesion real. |
| HU-09 | EP-04 | I | Marcas legadas y escritor probado; ensayo propio de marcar/deshacer/exportar pendiente. |
| HU-10 | EP-05 | I | Politica de bloqueo y continuidad probada, EV-13; no implica resolver las perdidas de captura. |
| HU-11 | EP-05 | I | Calidad GPS implementada; medir error espacial contra referencia cuando exista. |
| HU-12 | EP-06 | I | Preprocesamiento V0 legado; compatibilidad y bloques continuos nativos pendientes. |
| HU-13 | EP-06 | I | Features en V0 y piloto; versionar contrato entre entrenamiento e inferencia. |
| HU-14 | EP-07 | I | Baseline V0 legado; detector automatico de ZIP nativo pendiente. |
| HU-15 | EP-07 | P | Sensibilidad temporal del piloto; completar estudio V0. |
| HU-16 | EP-07 | P | Dataset local/externo construido; normales candidatos y etiquetas requieren revision. |
| HU-17 | EP-07 | P | RF/umbral y transferencia medidos; evaluar inferencia continua en datos reservados. |
| HU-18 | EP-08 | I | Asociacion GPS y cortes; error espacial real pendiente. |
| HU-19 | EP-10 | I | Mapa V0 local; plataforma y publicacion central por implementar. |
| HU-20 | EP-09 | P | Base y flujo con cuentas reales verificados (T-16/EV-16); integracion completa de plataforma y aceptacion de HU pendientes. |
| HU-21 | EP-09 | P | JWT, cliente web, renovacion/cierre y permisos probados con dos cuentas reales; idempotencia, cola durable y despliegue pendientes. |
| HU-22 | EP-10 | P | Seleccion local; filtros por fecha/tipo/area mediante API pendientes. |
| HU-23 | EP-11 | P | Metricas de ventanas disponibles; matching y metricas por evento pendientes. |
| HU-24 | EP-11 | N | FP/km requiere detector continuo y referencia revisada sobre recorrido completo. |
| HU-25 | EP-11 | N | Repetibilidad requiere pasadas comparables e identidad de defectos revisada. |
| HU-26 | EP-11 | P | Diagnostico de montaje y perdidas; ensayos controlados pendientes. |

Recuento de HU: **11 I, 13 P, 2 N**. Las tareas tecnicas y las historias tienen
granularidad distinta; no se afirma que el 42,3 % de HU I cumpla el 50 % de tareas.

## 4. Subtareas ejecutables de Etapa 3

Pendiente = planificada y no completada. Parcial = hay codigo/evidencia previa,
pero falta el cierre indicado. Prioridad A: proximo trabajo; B: integrar antes
de validacion; C: respaldo o continuidad. Responsable de todas: Pablo, con apoyo
tecnico; los ensayos fisicos dependen de su telefono y disponibilidad.

| ID | Padre | Prioridad | Estado al corte | Trabajo y evidencia de cierre | Dependencia |
|---|---|---|---|---|---|
| E3-01 | T-07, HU-07 | A | Parcial | Contrato local y perfiles probados (EV-12); falta resolver preview/entrega y paquete ejemplo con ensayo fisico. | EV-04, EV-12 |
| E3-02 | T-09, HU-09 | A | Pendiente | Captura propia detenida: dos marcas, deshacer una, cierre y lectura; CSV/ZIP y resultado auditado. | E3-01, telefono |
| E3-03 | T-10, HU-10/11 | A | Verificada | Politica compartida y estados V0/API/exportacion, bloques continuos y ventanas con cobertura GPS probados; inspeccion preservada (EV-13). | EV-13 |
| E3-04 | T-17, HU-21 | A | Verificada | API local con carga, trabajo, resultados y mapa en modo inspeccion; ZIP real procesado y pruebas automatizadas (EV-12). No cierra el padre T-17. | Contrato local E3-01 |
| E3-05 | T-16, HU-20 | A | Verificada | Migraciones, PostGIS, restricciones y rol backend comprobados; flujo integrado con dos cuentas Auth reales y ZIP propio aprobado (EV-15/16). | Proyecto Supabase |
| E3-06 | T-17, HU-21 | B | Verificada | Dos cuentas confirmadas, registro/login cliente, renovacion/cierre reales e aislamiento comprobados en API y Edge (EV-16). La APK tiene su subtarea separada. | E3-04, E3-05, proyecto Supabase |
| E3-07 | T-17, HU-21 | B | Parcial | Repositorio y flujo real de dos cuentas aprobados (EV-16); recuperacion probada en SQLite. Faltan cola durable, reintentos e idempotencia. | E3-04, E3-05 |
| E3-08 | T-17, HU-21 | B | Parcial | Docker, variables, healthcheck, preflight HTTPS/TLS, cuotas, backup y retencion preparados (EV-16). Faltan conexion Railway, construccion de imagen, TLS upstream, restauracion y URL publica. No se contrato servicio. | E3-06, E3-07, cuenta/presupuesto |
| E3-09 | T-17, HU-07/21 | B | Pendiente | Conectar subida APK con token y reintentos; conservar archivo local offline y demostrar sincronizacion. | E3-06, E3-07, E3-08, telefono |
| E3-10 | T-18, HU-19/22 | B | Parcial | Mapa, historial y descarga privados funcionando en cliente web con dos cuentas reales (EV-16). Faltan filtros por fecha/tipo/area. | E3-05, E3-06, E3-07 |
| E3-11 | T-18, HU-19/22 | B | Pendiente | Vista publica solo de observaciones autorizadas; probar que no revela propietario, ZIP ni trayectoria privada. | E3-10 |
| E3-12 | T-04/06, HU-03/26 | A | Pendiente | Instrumentar pantalla, tiempos de recepcion, cola y descartes por flujo; medir estado actual bajo protocolo fijo. | Telefono, EV-03 |
| E3-13 | T-04/06, HU-03/26 | B | Pendiente | Aplicar mejora segun diagnostico y repetir pruebas encendida/bloqueada; tabla antes/despues de descartes, huecos y consumo. | E3-12, telefono |
| E3-14 | T-08, HU-08/25 | A | Parcial | Completar ficha y fijar protocolo de pasadas comparables. Reservar recorrido de evaluacion y registrar incertidumbre 2-3 s. | Datos reales de captura |
| E3-15 | T-13/15, HU-14/17/24 | B | Pendiente | Inferencia continua: ventanas sin marcadores, exclusion de huecos, contrato de features y agrupacion en episodios; demo y pruebas. | E3-03, E3-14 |
| E3-16 | T-12, HU-23/24 | B | Pendiente | Matching uno-a-uno; metricas por evento y FP/km con recorrido revisado. Registrar casos no evaluables. | E3-15, referencias |
| E3-17 | T-08/12/14/15, HU-16/25/26 | B | Pendiente | Pasadas comparables y evaluacion reservada; congelar configuracion antes de prueba final, revisar normales y falsos positivos. | E3-14, E3-15, E3-16, terreno |
| E3-18 | T-11, HU-15 | C | Pendiente | Estudio de sensibilidad V0 con parametros fijados y resultados comparables. | Datos y protocolo |
| E3-19 | T-03/05, HU-04/06 | C | Pendiente | Resolver y registrar decision sobre Fused/Room; si se mantienen, implementar y verificar literalmente. | Revision de compromisos |
| E3-20 | HU-01/21/26 | B | Pendiente | Validacion integrada: permisos de dos cuentas, ZIP invalido, reintentos, dos cargas simultaneas y reinicio; latencia/memoria con entorno documentado. | E3-07, E3-08, E3-10 |
| E3-21 | HU-01, documentacion | A | Pendiente | Registrar cambios en Git de Python/Android, ADR y version de entrega; informe con enlaces a resultados. | Revision de cambios existentes |
| E3-22 | Retroalimentacion | A | Pendiente externo | Registrar comentario de Etapa 2, acciones y comprobaciones; actualizar plan si modifica prioridades. | Correo del profesor |

E3-21/E3-22 y pruebas complementan la rubrica; no aumentan por si mismas el
numerador de las 18 T. E3-15 no se considera resuelta por ejecutar el clasificador
solo en ventanas elegidas con las anotaciones.

## 5. Camino al umbral y decisiones

Primera ruta de referencia definida al inicio: **T-07, T-09, T-10 y T-16**.
T-10 se verifica el 10/10: ahora la ruta para pasar de 6 a 9 es **T-07, T-09 y T-16**.
Se eligieron por brechas concretas y evidencias obtenibles: contrato, prueba
integrada de anotacion, calidad y persistencia central. No se cuentan hasta
cumplir sus criterios; T-07 depende de resolver el alcance de entrega preview/V1.

T-17 y T-18 son objetivos de la plataforma, adicionales a esos cuatro cierres:
si tambien se verifican, el recuento seria **11/18 = 61,1 %**. Es una proyeccion,
no el avance actual. Cerrar T-04/T-06 mediante ensayos es valioso y puede cambiar
la ruta de trabajo; cada cierre real se contabiliza una sola vez.

Al comenzar una tarea: registrar criterio, entradas y dependencias. Al cerrarla:
enlazar commit, prueba/demo, resultado, fecha real y limitaciones. Actualizar
estado, evidencia y recuento juntos. Si falla, registrar fallo y siguiente accion.
Se mantiene pendiente cualquier tarea sin evidencia de cierre.

## 6. Registro de cambios del backlog

| Fecha | Cambio | Motivo | Alcance |
|---|---|---|---|
| 2026-10-09 | Se crea corte Etapa 3 con 18 T y 26 HU conservadas. | Usuario solicita plan verificable para el 50 %. | Revision tecnica local; retroalimentacion docente pendiente. |
| 2026-10-09 | Lectura nativa reconocida como implementada para inspeccion. | EV-04 posterior al backlog del 27/09. | HU-07/T-07 siguen parciales por contrato y ensayo integrado. |
| 2026-10-09 | Cinco T con alcance tecnico verificado y ocho parciales. | Codigo, informes y tests sostienen criterios operativos explicitos. | No cambia objetivos ni acredita validacion completa de HU. |
| 2026-10-09 | Se desglosan usuarios, API, despliegue, mapa y pruebas. | Propuesta de plataforma discutida con Pablo. | Subtareas planificadas; proveedor/contratacion/despliegue aun pendientes. |
| 2026-10-09 | E3-04 verificada; T-17/HU-21 pasan de N a P y E3-07/10 quedan parciales. | API local y ZIP real comprobados, EV-12. | 5 V, 9 P, 4 N; avance T conserva 27,8 %. Sin cuentas ni servicio publicado. |
| 2026-10-10 | T-10/E3-03 verificadas; T-16/HU-20 pasan de N a P. | EV-13 calidad y EV-14 modelo/migracion/autorizacion. | 6 V, 9 P, 3 N: 33,3 %. PostgreSQL/Supabase reales pendientes; cambios aun en copia de trabajo, E3-21 pendiente. |
| 2026-10-16 | Conexion real, migraciones PostGIS y rol backend comprobados. | EV-15: siete pruebas runtime con rollback, geometria/FK/rangos y arranque central 200/401. | Se conserva el recuento hasta validar el flujo con cuentas Auth reales. Sin despliegue ni cambios Android. |
| 2026-10-16 | T-16 y E3-05/E3-06 verificadas; E3-08 parcial. | EV-16: dos cuentas confirmadas, ZIP real en ambas, aislamiento 404 y cliente probado en Edge; preparacion de despliegue y respaldo local. | 7 V, 8 P, 3 N: 38,9 %. Publicacion HTTPS y subida APK pendientes; no implica aceptacion academica de HU. |
