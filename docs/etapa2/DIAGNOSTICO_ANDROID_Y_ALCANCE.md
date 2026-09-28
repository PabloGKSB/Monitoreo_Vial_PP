# AnotadorVial: diagnostico y alcance integrado de Etapa 2

Fecha: 2026-09-26. Lectura de codigo; no compilacion ni ensayo en dispositivo.
Proyecto confirmado por Pablo como el utilizado en los recorridos:
`C:/Users/GOMEPAB/AndroidStudioProjects/AnotadorVial`.
Equipo declarado: Xiaomi Mi 10T, Android 12, compilacion SKQ1.211006.001.
No se verificaron por ADB sensores instalados, firmware, version MIUI ni APK.

## 1. Alcance acordado y distinciones

Pablo solicita abarcar la Etapa 2 integrando la propuesta de evolucion. Se
interpreta como cubrir diseno, backlog, protocolo e implementacion inicial
coherente con Etapa 1, NO como aprobacion de implementar inmediatamente todas
las fases de inferencia movil. Captura propia es el incremento prioritario;
ML en Android se disena como extension posterior, condicionada a validacion.
La entrega del 2/10 debe distinguir lo demostrado de lo pendiente.

| Propuesta | Compromiso original | Tratamiento para Etapa 2 |
|---|---|---|
| Captura IMU/GPS propia, inicio/fin, exportacion | OE2; HU02-07; T01-07 | Disenar completamente el incremento y priorizar implementacion demostrable. |
| Conservar overlay y marcas | OE3; HU08-09/16; T08-09 | Mantener funcionalidad, formalizar retraso y metadata. |
| Calidad, relojes y features | OE4; HU10-13 | Reutilizar Python; especificar captura equivalente, sin duplicar pipeline. |
| Comparacion Sensor Logger/captura propia | OE2/3/6; RE11/12 | Prueba de compatibilidad/calidad, no considerar Sensor Logger verdad absoluta. |
| Baseline frente a ML | OE4/6; HU14-17/23 | Conservar piloto exploratorio y distinguir umbral supervisado de detector V0. |
| Buffer, baseline e inferencia en Android | Evolucion no exigida explicitamente | Especificar interfaces; no declarar implementacion ni nuevo compromiso inmediato. |
| Notificaciones y revision de predicciones | Ampliacion funcional | Diferir; no generar verdad de terreno a partir de confirmacion inducida. |
| API/PostGIS/dashboard | OE5; HU20-22 | Mantener en backlog como extension; acordar calendario, no eliminar objetivo. |

El 100 % de tareas de diseno requiere evidencia y revision. Este diagnostico
aporta a D01/D05/D07/D10, no cierra automaticamente esas tareas ni otorga nota.

## 2. Arquitectura actual comprobada

| Origen | Relacion | Destino |
|---|---|---|
| MainActivity | setContent / acciones Compose | AnotadorVialApp y funciones de sesion del mismo archivo |
| MainActivity.onResume | Si permiso overlay, iniciar servicio | OverlayService |
| MainActivity y OverlayService | Consultan/modifican estado global compartido | SesionActual |
| Ambos puntos de entrada | Iniciar, registrar, deshacer, finalizar | Funciones globales de MainActivity.kt |
| Funciones de sesion | FileWriter por operacion | CSV en external-files/Documents |
| compartirCSV | URI temporal de lectura | FileProvider -> selector de compartir |

No existe RecordingService de captura ni Collector IMU/GPS en los archivos de
produccion inspeccionados. El foreground actual pertenece al overlay; no es
un capturador de sensores. Persistencia Room y cliente de ubicacion no figuran
en dependencias de app. UI usa Compose y el overlay vistas WindowManager.

Referencias locales de codigo (lineas de la revision):

- MainActivity.kt:86 modelo Anotacion; :106 SesionActual en memoria.
- :1088 iniciarNuevaSesion crea CSV, referencia elapsedRealtime y marca inicio.
- :1184 finalizarSesion escribe FIN antes de cerrar el estado logico.
- :1234 registrarEventoSesion usa currentTimeMillis y elapsedRealtime.
- :1326 deshacerUltimaAnotacion reescribe el CSV completo.
- :1515/:1568/:1605 creacion, append y reescritura via FileWriter.
- :1719 vibrar; :1867 compartirCSV con FileProvider y permiso de lectura.
- OverlayService.kt:91 onStartCommand devuelve START_NOT_STICKY; :147 foreground;
  :1278 feedback de 70 ms tras evento registrado.
- AndroidManifest.xml: overlay specialUse, sin permisos de ubicacion.
- app/build.gradle.kts: minSdk26, compileSdk37, targetSdk37, versionName1.0.

La version SDK objetivo del proyecto no es la version del telefono. No se propone
bajar targetSdk para evitar implementar correctamente los permisos/estados.

## 3. Riesgos antes de ampliar captura

| Riesgo | Evidencia y consecuencia | Tratamiento propuesto |
|---|---|---|
| Estado solo en proceso | SesionActual se pierde al morir proceso; no se vio reconstruccion desde disco. | SessionRepository persistente; marcar incompleta y recuperar, no reanudar silenciosamente. |
| I/O en acciones de UI | FileWriter directo desde callbacks, sin despachador de escritura dedicado. | Un escritor serializado fuera de UI; lotes/buffer acotados para muestras. |
| Deshacer no transaccional | FileWriter(false) trunca; un fallo puede dejar CSV parcial aunque se restaure lista en memoria. | Escritura temporal y reemplazo seguro o registro de revision; probar fallo de disco. |
| Dos entradas a estado compartido | Pantalla y overlay llaman mismas funciones; anadir threads de sensores ampliaria riesgo de carreras. | Un propietario de sesion/comandos serializados; snapshots para UI. |
| GPS aun no disponible en app | Sin permisos ni collector. | Servicio location y permisos/versiones probados; denegacion debe producir estado claro. |
| Feedback introduce posible senal | vibrar tras registrar evento. | Control explicito de feedback y prueba detenida; no afirmar causa de picos historicos. |
| Pruebas Android insuficientes | Test local observado solo comprueba 2+2=4. | Tests de reloj, escritura, cierre, deshacer, recuperacion y dispositivo. |
| Perdidas/cierre por sistema | START_NOT_STICKY no reconstruye sesion; foreground no prueba continuidad. | Ensayo pantalla apagada, proceso interrumpido y sesion larga en Mi 10T. |
| Almacenamiento de ubicaciones | Anadir GPS cambia sensibilidad de datos; allowBackup=true actual. | Revisar reglas de backup y exportacion; no publicar ubicaciones por defecto. |

No se afirma que ya haya ocurrido corrupcion o perdida en las grabaciones.
Estos son riesgos derivados del codigo y de la ampliacion propuesta.

## 4. Adaptacion incremental propuesta

Nuevos archivos previstos, a confirmar durante implementacion:

| Archivo/modulo | Responsabilidad |
|---|---|
| session/SessionRepository.kt | Unico propietario del estado persistente y comandos de inicio/fin/anotacion. |
| time/SessionClock.kt | Anclas UTC/monotono; reloj inyectable para pruebas. |
| sensor/SensorCollector.kt | Disponibilidad/propiedades y muestras nativas fuera de UI. |
| sensor/LocationCollector.kt | Ubicacion, edad de fijacion, precision, campos disponibles. |
| service/RecordingService.kt | Captura independiente de pantalla y overlay, cierre ordenado. |
| storage/TripStorageManager.kt | Persistencia local con escritura serializada/lotes y recuperacion. |
| storage/SessionExporter.kt | Exportacion versionada, archivos por sensor, hashes y ZIP. |
| data/RecordingModels.kt | Muestras y metadata tipadas; rotacion conserva componentes/semantica, no forzar todo a XYZ. |

Room/DAOs siguen la decision de Etapa 1; no elegir CSV como sustituto de Room
sin registrar una desviacion justificada. CSV/JSON es el formato de exportacion,
independiente de la persistencia usada mientras se captura.

Modificar gradualmente MainActivity.kt (UI observa estado y envia comandos),
OverlayService.kt (mismos comandos, no colecta sensores), manifest/permisos,
dependencias, exportacion y tests. Conservar temas, recursos visuales y funciones
de compartir que sean compatibles; extender MIME a ZIP donde corresponda.
Mantener exportacion legacy de anotaciones hasta tener adaptador nuevo probado.
No reorganizar todas las pantallas ni cambiar el paquete solo por estilo.

SensorBuffer/SignalProcessor/FeatureExtractor/DetectionEngine quedan como
interfaces futuras: captura y persistencia primero. Buffer de analisis no es
almacenamiento RAW. Su horizonte debe cubrir ventana, retraso y contexto; 2-3 s
no garantiza conservar un impacto marcado 3 s despues. Dimensionar por tiempo
y tasa medida con limite de memoria, no por suponer exactamente 100 Hz.

## 5. Relojes y servicio de captura

Usar timestamp nativo de SensorEvent en nanosegundos, basado en elapsedRealtimeNanos;
anotacion nueva conserva tiempo monotono al pulsar y epoch para presentacion.
El GPS ofrece elapsedRealtimeNanos para ordenar fijaciones en el mismo arranque;
no reemplazarlo por la hora de llegada del callback. Guardar tambien su epoch
original y relacion con ancla, sin asumir que todos los epochs vienen del mismo
reloj. Fuentes: [SensorEvent](https://developer.android.com/reference/android/hardware/SensorEvent#timestamp)
y [Location](https://developer.android.com/reference/android/location/Location#getElapsedRealtimeNanos()).

El servicio actual specialUse del overlay no sustituye el servicio de ubicacion.
Disenar inicio explicito desde pantalla visible, permisos de ubicacion y estado
de GPS; aplicar requisitos por version de Android/target. Para sistemas modernos
hay requisitos especificos del tipo location, que deben probarse aparte del
Android12 de Pablo. No pedir ubicacion en segundo plano por defecto sin necesidad.
Fuente: [tipos de foreground service](https://developer.android.com/develop/background-work/services/fgs/service-types#location).

## 6. Incrementos y evidencia de aceptacion

| Orden | Incremento | Criterio observable | HU/T |
|---|---|---|---|
| A0 | Baseline Android reproducible | Build actual y prueba iniciar/marcar/deshacer/finalizar/compartir; respaldo versionado. | HU09/T09 |
| A1 | Sesion/reloj/escritor aislados | UI y overlay conservan comportamiento; fallo de escritura visible; cierre idempotente. | HU02/06, T01/05/06 |
| A2 | Captura IMU | Solicitar ~100Hz; conservar tiempos y disponibilidad; contar muestras/gaps, no prometer tasa exacta. | HU03/05, T02/04 |
| A3 | GPS y exportacion | Sesion con fijaciones/precision o ausencia explicita; ZIP nuevo legible en PC. | HU04/07, T03/07 |
| A4 | Calidad en Mi 10T | Captura corta y representativa, pantalla apagada, permisos denegados, cierre/recuperacion y bytes/bateria registrados. | HU10/11, RE13 |
| A5 | Integracion Python | Adaptador por version y regresion legacy; mismos RAW reproducen analisis sin desplazar relojes. | HU12/13/18 |

El primer incremento demostrable de captura es A2; el flujo completo prioritario
requiere A3-A5. No declarar A2 como cumplimiento completo de OE2. No se ejecutaron
estos incrementos en este diagnostico, ni se promete su cierre sin verificar build
y dispositivo. El calendario concreto se ajusta despues de A0.

Comparacion con Sensor Logger: mismas condiciones documentadas y mismas unidades;
medir conteos, distribucion de dt, gaps, duracion, archivo y desfase. Si se ejecutan
ambas apps simultaneamente, documentar esa carga adicional; no atribuir diferencias
a precision fisica sin referencia independiente. Nueva captura no permite aplicar
sin comprobacion las features entrenadas con semantica de otro exportador.

## 7. Cierre de Etapa 2

Integrar este diagnostico con [backlog](BACKLOG.md), [diseno](DISENO_TECNICO.md),
[contrato](CONTRATO_DATOS.md) y [protocolo](PROTOCOLO_EXPERIMENTAL.md).
Pendiente: actualizar diagramas, validar paquete ejemplo, acordar alcance API,
completar evidencia del profesor e informe, registrar commits. La propuesta no
convierte automaticamente todas las funcionalidades futuras en entregables del 2/10.
