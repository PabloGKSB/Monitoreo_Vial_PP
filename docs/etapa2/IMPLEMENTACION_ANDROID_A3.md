# Incremento A3: sensores complementarios y GPS

Fecha: 2026-09-27. Proyecto Android: `C:/Users/GOMEPAB/AndroidStudioProjects/AnotadorVial`.
Estado: implementacion y verificacion de compilacion/JVM; aceptacion fisica pendiente.
Respaldo previo: `outputs/reports/AnotadorVial_pre_a3_20260927_201536.zip`.

## Captura incorporada

| Flujo | API / semantica | Archivo |
|---|---|---|
| Aceleracion total | TYPE_ACCELEROMETER, incluye gravedad, m/s2, ejes del dispositivo | accelerometer.csv |
| Giroscopio | TYPE_GYROSCOPE, rad/s, ejes del dispositivo | gyroscope.csv |
| Gravedad | TYPE_GRAVITY, estimacion Android, m/s2 | gravity.csv |
| Aceleracion lineal | TYPE_LINEAR_ACCELERATION, estimacion Android, m/s2 | linear_acceleration.csv |
| Rotacion | TYPE_ROTATION_VECTOR, qx/qy/qz/qw, accuracy y numero de componentes | rotation_vector.csv |
| GPS | LocationManager.GPS_PROVIDER, WGS84, epoch y tiempo monotono propios | gps.csv |

Se solicitan 100 Hz a los sensores y un intervalo GPS de 1 s. Son solicitudes,
no tasas garantizadas. Las tasas visibles se calculan a partir de muestras escritas.
El acelerometro es obligatorio para iniciar captura; los otros sensores pueden
estar ausentes o fallar al registrarse, con estado y advertencia explicitos.

No se filtran los RAW ni se transforma automaticamente a vertical terrestre.
Gravedad, aceleracion lineal y rotacion pueden ser sensores virtuales estimados por
Android, no nuevas mediciones fisicas independientes. No se afirma equivalencia
numerica con Sensor Logger sin una comparacion experimental controlada.

## GPS, permisos y servicio

- Preferencia persistente Registrar GPS, habilitada inicialmente. Se puede cambiar
  antes del recorrido, no durante una captura.
- Al iniciar, se solicitan ubicacion precisa y aproximada juntas. GPS requiere
  permiso preciso en esta implementacion. Si no esta concedido o el proveedor esta
  apagado, se ofrece revisar ajustes o continuar explicitamente sin GPS.
- No se solicita ACCESS_BACKGROUND_LOCATION. El inicio con GPS se hace desde la
  pantalla visible; la burbuja abre la app para que el usuario confirme ese inicio.
- El servicio pasa al tipo foreground location solo despues de comprobar permisos,
  proveedor e inicio desde UI. Una denegacion al activar ese tipo deja GPS con error
  explicito y permite conservar captura IMU.
- No se carga una ultima posicion conocida como si fuera una fijacion nueva. Se
  registran callbacks de ubicacion y se conservan sus tiempos originales.
- Se distinguen GPS deshabilitado para la sesion, falta de permiso, proveedor
  apagado/no disponible, espera de fijacion, recepcion y ausencia de fijacion reciente.
- Mas de 10 s desde la ultima fijacion cambia el indicador a Sin fijacion reciente.
  Es un umbral de interfaz, no un criterio validado de calidad espacial.
- Si GPS estaba apagado al iniciar y se continuo solo con sensores, habilitarlo luego
  no cambia retroactivamente la sesion: debe iniciarse otra captura con GPS.

Decision tecnica A3: se utiliza LocationManager del SDK, sin agregar Google Play
Services. El backlog original mencionaba FusedLocationProviderClient; se registra
esta desviacion para mantener captura GPS explicita y evitar una dependencia nueva.
No se declara T03 implementada literalmente con FusedLocationProviderClient.

Referencias de API: [servicios foreground de ubicacion](https://developer.android.com/develop/background-work/services/fgs/service-types#location),
[sensores de movimiento](https://developer.android.com/develop/sensors-and-location/sensors/sensors_motion),
[LocationManager](https://developer.android.com/reference/android/location/LocationManager).

## Contrato implementado: capture-preview-2

El ZIP conserva entradas planas: los seis CSV de flujo, `metadata.json` y el CSV
legacy de anotaciones. Se mantiene el sufijo local `_imu` del directorio para que
el historial anterior siga encontrandolo. El sufijo ya no describe todo el contenido.

Todos los flujos tienen este prefijo de columnas:

```text
sensor_timestamp_ns,epoch_ms_derived,seconds_elapsed
```

`sensor_timestamp_ns` contiene SensorEvent.timestamp o Location.elapsedRealtimeNanos,
segun el flujo. Se relacionan con el mismo origen monotono de sesion; no es epoch.
Se conserva el entero decimal, sin convertirlo primero a float. El epoch derivado
usa el ancla monotona/civil del servicio, como en A2.

Para acelerometro, giroscopio, gravedad y aceleracion lineal siguen `x,y,z`.
Rotacion agrega:

```text
qx,qy,qz,qw,heading_accuracy_rad,value_count,sensor_accuracy
```

Se conserva qw si Android lo entrega; si falta queda vacio. No se reconstruye
silenciosamente un componente ni se sustituye el vector de rotacion por Euler.
El accuracy negativo entregado por la API se conserva como tal, no como precision
positiva. El consumidor debe interpretar los valores segun la API Android.

GPS agrega:

```text
location_epoch_ms,latitude,longitude,altitude_m,speed_mps,bearing_deg,
horizontal_accuracy_m,vertical_accuracy_m,speed_accuracy_mps,
bearing_accuracy_deg,provider,is_mock
```

El epoch GPS original NO se sustituye por el epoch derivado ni por hora de callback.
Altitud esta referida al elipsoide WGS84, velocidad en m/s, rumbo en grados y
precision horizontal/vertical en metros. La UI convierte velocidad a km/h solo
para presentacion y la identifica como ultima velocidad recibida.
Los campos opcionales se escriben vacios cuando los indicadores has... de Android
son falsos. No se inventan ceros. Ubicaciones de proveedor simulado quedan marcadas.

Se crean cabeceras de todos los flujos incluso si un sensor esta ausente o GPS no
recibe fijaciones. Existencia de CSV no significa disponibilidad: revisar conteos,
`sensor_states`, `sensors`, `gps_requested`, `gps_registered` y advertencias.

Metadatos incluyen estado de cierre, propiedades de sensores, relojes, semantica,
conteos, Hz efectivos, intervalo maximo, intervalos superiores a 100 ms, tiempos no
crecientes, descartes de cola y muestras pendientes. En GPS un intervalo de 1 s
supera normalmente 100 ms: ese contador NO es una cuenta de perdidas ni de gaps GPS.
La cola de 4096 elementos se comparte entre todos los flujos; descartes son globales.

`gps_available` al cierre significa que se escribio al menos una fijacion, no una
prueba de precision suficiente. `COMPLETED` describe cierre sin error fatal, no
validacion cientifica. Revisar siempre `quality_warnings`, especialmente GPS sin
fijaciones, sensores ausentes o sin muestras y descartes. Se conserva el ultimo
estado GPS, timestamp monotono y edad de fijacion al cerrar.

## Archivos y compatibilidad

- `CaptureSamples.kt`: modelos tipados y esquema/serializacion por flujo.
- `GpsAccess.kt`: preferencia, permiso preciso y disponibilidad del proveedor.
- `GpsCollector.kt`: suscripcion GPS, conversion con opcionales y liberacion.
- `RecordingService.kt`: integra sensores, GPS, tipos foreground y metadatos.
- `ImuSessionWriter.kt`: reutiliza cola/escritor; ahora admite muestras de seis flujos.
- `CaptureState.kt` y `MonitoringApp.kt`: estado de sensores, permisos y presentacion.
- Manifest: permisos de ubicacion y tipo location. No se agregan dependencias.
- Reglas de backup: Documents de la app se excluye de nube y transferencia automatica
  declarada, por contener ubicaciones. Exportacion manual sigue disponible.

No se reescriben archivos previos. El historial sigue leyendo las anotaciones
legacy y metadatos anteriores. `capture-preview-2` NO es el perfil V1 completo
propuesto en CONTRATO_DATOS.md ni el formato de Sensor Logger. El adaptador Python,
hashes de exportacion, Room y esquema definitivo siguen pendientes.

## Pruebas y aceptacion

El parche `patches/android_a3_permission_state.patch`, antes pendiente por limite
de uso, ya fue aplicado a `ui/MonitoringApp.kt`. La respuesta de permisos GPS se
conserva con rememberSaveable y se consume desde LaunchedEffect al volver la UI
a primer plano. Se evita depender de una coroutine de la instancia anterior de
la pantalla. Falta comprobar fisicamente la rotacion durante el dialogo y entre
la respuesta del permiso y el retorno a la app, tanto concediendo como denegando.
Verificacion posterior al parche: `testDebugUnitTest assembleDebug
assembleDebugAndroidTest lintDebug --offline` finalizo con BUILD SUCCESSFUL,
27 pruebas JVM aprobadas y sin errores de Lint. Persisten advertencias; las pruebas
instrumentadas se compilaron, pero no se ejecutaron en dispositivo.

Siete pruebas JVM adicionales cubren componentes de rotacion, opcionales vacios,
ambos relojes GPS, ubicacion simulada, drenado de seis flujos, GPS solo con cabecera
y rechazo de nombres de flujo desconocidos. Se conservan las veinte pruebas previas.
Compilar y probar serializacion no demuestra recepcion fisica de GPS o sensores.

Procedimiento propuesto en Xiaomi, fuera de una captura de investigacion:

1. Actualizar mediante Run en Android Studio, sin desinstalar ni borrar datos.
2. Al aire libre y con el vehiculo detenido, iniciar `PRUEBA_GPS` y conceder
   ubicacion precisa mientras se usa la app. Esperar una fijacion nueva.
3. Comprobar conteos de los cinco sensores, GPS, precision y edad de fijacion.
4. Registrar/deshacer una marca, finalizar y exportar. Revisar los seis CSV,
   metadatos, filas GPS reales y preservacion del CSV de anotaciones.
5. Repetir denegando permiso, dando solo aproximado y apagando GPS. No deberian
   aparecer posiciones ficticias ni anunciar recepcion sin fijaciones.
6. Probar interrupcion de GPS durante captura y restablecimiento; revisar estados
   y tiempos RAW. Comparar captura corta con app visible y pantalla apagada.

La continuidad en segundo plano/pantalla apagada, bateria y estabilidad del montaje
deben medirse en dispositivo. No se agrego wakelock ni se garantiza continuidad a
partir de foreground solamente. No se ejecutaron pruebas fisicas en este incremento.
Mapas, graficas, magnetometro/brujula/no calibrados, detector y ML movil no se
implementaron aqui. No se crearon commits; versionado Git Android pendiente.
