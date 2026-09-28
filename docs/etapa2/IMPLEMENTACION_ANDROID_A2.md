# Incremento Android A2: captura IMU inicial

Fecha: 2026-09-27. Estado: implementado y compilado; aceptacion en dispositivo pendiente.

Proyecto modificado: `C:\Users\GOMEPAB\AndroidStudioProjects\AnotadorVial`.
No se debe abrir la carpeta Python como si fuera este proyecto Android.
Respaldo anterior a la captura: `outputs/reports/AnotadorVial_pre_imu_20260926_131438.zip`.
Los parches A2, revision y cierre de `patches/` documentan los cambios en orden;
son registros para revision, no deben reaplicarse sobre el proyecto ya actualizado.

## Alcance implementado

- Inicio automatico de captura al iniciar una sesion del anotador, desde la app o la burbuja.
- `SensorManager`: acelerometro y giroscopio si esta disponible. Periodo solicitado: 10000 us (100 Hz); no es una frecuencia garantizada.
- Servicio foreground separado del overlay, con notificacion de captura y registro de sensores en un `HandlerThread`.
- Cola limitada a 4096 muestras y escritor CSV dedicado. Si la cola se llena, se cuentan los descartes; no se bloquea el callback esperando al disco.
- Al finalizar, se desregistran sensores, se drena la cola, se vacian/sincronizan y cierran archivos y se actualizan metadatos antes de habilitar otra captura.
- Pantallas de sesion y cierre con estado, conteos, frecuencia efectiva, descartes y errores. Se permite desplazamiento vertical en pantallas pequenas.
- ZIP compartible con CSV RAW, metadatos y CSV de anotaciones. Se conserva el boton anterior de compartir solo anotaciones.
- Vibracion propia del anotador desactivada mientras la captura esta ocupada, para reducir artefactos inducidos. No controla vibraciones de otras apps o del sistema.

## Responsabilidades de los archivos

| Archivo Android | Responsabilidad |
|---|---|
| `capture/RecordingService.kt` | Ciclo de captura, suscripcion/desuscripcion, relojes, notificacion y metadatos de cierre. |
| `capture/ImuSessionWriter.kt` | Cola acotada, escritura fuera de UI, drenado y estadisticas temporales. |
| `capture/CaptureState.kt` | Estado observable en Compose y puente de inicio/fin hacia el servicio. |
| `capture/CapturePanel.kt` | Estado visible, exportacion en hilo de trabajo y selector para compartir. |
| `capture/ImuArchive.kt` | Empaquetado ZIP, exclusion de temporales y proteccion contra sobrescritura. |
| `MainActivity.kt` | Integra inicio/fin IMU con el anotador existente y bloquea reinicios durante el cierre. |
| `AndroidManifest.xml` | Declara el servicio de captura `specialUse`, no exportado. |

No se agregaron dependencias externas. Se usan Android SensorManager/Service/Handler,
Compose existente, FileProvider existente y las bibliotecas JVM de archivos, concurrencia
y ZIP. La escritura frecuente de sensores queda fuera del hilo de interfaz; las marcas
manuales conservan el almacenamiento A1a, que todavia realiza E/S sincrona de baja frecuencia.

## Contrato real de esta version

Esquema **`imu-preview-1`**, no la exportacion RAW V1 completa propuesta en el contrato general.
Directorio: `Android/data/com.monitoreovial.anotador/files/Documents/<anotaciones>_imu/`.
La interfaz de compartir evita depender del acceso manual a ese directorio restringido.

Contenido del ZIP, con entradas planas:

- `accelerometer.csv`: obligatorio si pudo iniciarse el escritor.
- `gyroscope.csv`: cuando existe giroscopio.
- `metadata.json`: estado, relojes, semantica, dispositivo, conteos y calidad.
- CSV de anotaciones existente, con nombre original y sin cambiar sus cinco columnas.

Columnas de sensores: `sensor_timestamp_ns,epoch_ms_derived,seconds_elapsed,x,y,z`.
El acelerometro incluye gravedad y usa m/s2 en ejes del dispositivo; NO es aceleracion
lineal ni vertical terrestre. El giroscopio usa rad/s en ejes del dispositivo.

Para cada muestra de tiempo nativo t y anclas t0/E0:

```text
seconds_elapsed = (t - t0) / 1e9
epoch_ms_derived = E0 + trunc((t - t0) / 1e6)
effective_hz = (N - 1) * 1e9 / (t_last - t_first)
```

Se preserva el timestamp nativo completo como entero decimal. Metadatos guardan el
origen monotono IMU en texto para evitar perdida de precision en consumidores JavaScript.
La frecuencia se calcula sobre muestras escritas, no sobre la configuracion solicitada.
Tambien se registran intervalo maximo, intervalos superiores a 100 ms, tiempos no
crecientes, descartes de cola y muestras pendientes sin escribir.

Las anotaciones y la IMU tienen origen propio. `annotation_origin_monotonic_ms` permite
alinear `elapsed_ms` del anotador con los nanosegundos IMU mediante:

```text
t_referencia_ns = (annotation_origin_monotonic_ms + elapsed_ms) * 1e6
```

La precision de las marcas sigue limitada a milisegundos y al acto humano. Sus epoch
son de reloj civil; el epoch IMU es derivado. No se deben comparar ambos tiempos
ciegamente si el reloj civil cambia durante una sesion.
El retraso declarado de 2-3 s NO se resta de los RAW ni convierte la marca en impacto
exacto. Ese ajuste sigue siendo una hipotesis de analisis posterior con incertidumbre.

`COMPLETED` significa cierre de archivos sin error detectado, no calidad cientifica
validada. Puede coexistir con descartes o huecos que requieren revision. Un error o
ausencia de muestras esperadas produce `INCOMPLETE`. Una terminacion abrupta del proceso
puede dejar `RECORDING`: no debe reinterpretarse como captura completa.

## Verificacion ejecutada

`gradlew.bat testDebugUnitTest assembleDebug --offline`: compilacion y 15 pruebas JVM
aprobadas (una es la prueba aritmetica original). Las 7 nuevas pruebas cubren escritura,
relojes derivados, drenado, cola acotada, estadisticas, error de almacenamiento, ZIP y
proteccion contra sobrescritura/falta de metadatos.

Android Lint no pudo ejecutarse offline: falta `com.android.tools.lint:lint-gradle:32.3.1`
en cache. No es un resultado de Lint limpio ni un error de compilacion Kotlin.
ADB detecto un dispositivo autorizado modelo `M2007J3SY` (apollo). No se ha instalado
ni manipulado la app para esta verificacion; la deteccion USB no valida sensores o UI.

## Prueba de aceptacion pendiente en el Xiaomi

1. Abrir AnotadorVial en Android Studio y ejecutar Run sobre el telefono, fuera de una captura real.
2. Iniciar una sesion `PRUEBA_IMU`, con el vehiculo estacionado. Comprobar notificacion,
   estado Capturando IMU y conteos crecientes de ambos sensores.
3. Esperar al menos 30 s y registrar/deshacer una marca. Mover suavemente el telefono
   solo para esta prueba funcional, sin tratarla como evidencia vial.
4. Cambiar de app y volver. Revisar continuidad. Probar pantalla apagada por separado;
   el servicio foreground por si solo NO garantiza frecuencia ni evita suspension de CPU.
5. Finalizar, esperar IMU guardada y compartir ZIP. Verificar presencia y contenido de
   CSV/metadatos/anotaciones en PC, conteos, tiempos y ausencia de descartes.
6. Repetir una sesion y un inicio/fin rapido; comprobar que no se mezclan archivos y que
   los errores o cero muestras no aparecen como captura correcta.

## Limites y siguiente incremento

- Sin GPS propio, filtros, clasificacion ni inferencia movil. Este ZIP NO alimenta
  directamente el pipeline Python que exige GPS y el formato de Sensor Logger.
- No hay Room, historial recuperable desde UI ni recuperacion automatica tras muerte
  del proceso. Los archivos persisten, pero la sesion de interfaz sigue en memoria.
- Faltan prueba fisica, continuidad prolongada/pantalla apagada, bateria, montaje,
  errores de disco y flujo completo de compartir en el dispositivo.
- No se declara frecuencia garantizada, calibracion, validez de etiquetas o cumplimiento
  completo de una HU por compilar o pasar pruebas unitarias.
- GPS, contrato RAW definitivo, adaptador Python y recuperacion son trabajos siguientes.
  Sensor Logger sigue siendo la referencia para campanas mientras se acepta la captura propia.

La carpeta Android no tiene repositorio Git inicializado. Los cambios locales y sus
parches no sustituyen commits ni una version de entrega. No se crearon commits en este paso.
