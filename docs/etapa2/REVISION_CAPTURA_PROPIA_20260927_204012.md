# Revision de captura propia: 27/09/2026, 20:40:12

## Fuente y alcance

Archivo revisado en Downloads, sin modificar ni extraer sobre archivos existentes:
`monte_Verde_3_20260927_204012_792_anotaciones_imu_1790552517549.zip`.

- SHA-256: `5d31d4d107e34a07f23e44bd738b8d21bd2bfee18cca347d0efa6e321240687f`.
- Tamano ZIP: 1 134 139 bytes; comprobacion CRC interna sin errores.
- Ocho entradas: cinco CSV inerciales/orientacion, GPS, metadata.json y anotaciones.
- Esquema: capture-preview-2; dispositivo declarado por metadata M2007J3SY, Android 12.
- Estado: COMPLETED; error null; quality_warnings vacio.
- La revision recalculo intervalos y conteos desde los CSV con pandas/NumPy, leyendo
  nanosegundos como int64. No se utilizo el loader de Sensor Logger ni se evaluo ML.
- No se reproducen coordenadas en este documento por privacidad.

## Resultados recalculados

| Flujo | Muestras | Frecuencia efectiva | Mayor intervalo |
|---|---:|---:|---:|
| Acelerometro total | 9116 | 102.895 Hz | 9.718906 ms |
| Giroscopio | 9117 | 102.895 Hz | 9.718936 ms |
| Gravedad | 9115 | 102.895 Hz | 9.718906 ms |
| Aceleracion lineal | 9114 | 102.895 Hz | 9.718906 ms |
| Vector de rotacion | 9110 | 102.895 Hz | 9.718906 ms |
| GPS | 64 | 0.941 Hz | 5000.319581 ms |

Los cinco flujos inerciales tienen mediana de intervalo de 9.718646 ms,
sin intervalos mayores de 100 ms ni tiempos duplicados/decrecientes. Sus inicios
y finales no son exactamente simultaneos; diferencias pequenas de conteos no
demuestran perdida de muestras. Los seis conteos coinciden con metadata.json.
Se informan cero descartes de cola y cero muestras pendientes sin escribir.
Esto no prueba ausencia de cualquier perdida interna del sistema operativo.

No hay campos faltantes en los CSV inerciales. Las cuatro senales XYZ revisadas
no contienen valores no finitos. Los 9110 registros de orientacion conservan
los cinco valores informados por Android, incluido qw; la norma del cuaternion
esta entre 0.999999941 y 1.000000058. Esto demuestra consistencia numerica, no
exactitud absoluta de orientacion. heading_accuracy_rad vale cero en toda la
captura; no debe interpretarse como una demostracion de error fisico nulo.

## GPS

- Primera fijacion registrada: 21.127785 s desde origen del servicio IMU, unos
  21.295 s desde inicio del anotador. Explica la espera inicial de esta sesion;
  el ZIP no identifica por si solo la causa de la demora de recepcion.
- Ultima fijacion: 88.051069 s desde origen IMU.
- Mediana de intervalo: 1 s; minimo 0.907732 s.
- Un intervalo mayor de 2 s: de 23.127637 a 28.127956 s, duracion 5.000320 s.
- Precision horizontal informada: mediana 8.410961 m; rango 6.408077 a 114.723680 m.
- Las primeras fijaciones incluyen precisiones de 109-115 m. Las ultimas cinco
  reportan aproximadamente 6.4-6.8 m; la ultima, 6.620337 m.
- Ninguna fijacion se declara simulada; coordenadas en rangos validos. Esto no
  comprueba exactitud espacial contra una referencia externa.
- Rumbo y precision de rumbo estan ausentes en 56/64 filas; se conservan celdas
  vacias, no ceros inventados. La ausencia no indica por si sola un error del CSV.
- Mediana de velocidad informada: 0 m/s. El maximo de 2.47 m/s ocurre durante
  la fase de precision pobre; no se puede usar como prueba de movimiento real.

El contador `intervals_over_100ms = 63` en GPS es coherente con sus 63 intervalos
entre 64 fijaciones, normalmente separados por 1 s. NO significa 63 perdidas.
El arreglo vacio quality_warnings tampoco significa precision GPS validada:
actualmente no detecta precision horizontal pobre ni todos los huecos GPS.

## Relojes y anotaciones

Las anotaciones contienen solamente MONITOREO_INICIO y MONITOREO_FIN. Duracion
registrada: 88.833 s. NO hay marcas manuales BACHE, OTRO u otras categorias.
Por tanto, esta prueba no permite verificar un marcado manual ni el retraso
retrospectivo de 2-3 s respecto de una senal.

El origen IMU es posterior al origen monotono del anotador en 0.166732739 s.
Es un desfase entre inicios de modulos, no una discrepancia de reloj demostrada.
Para todos los CSV se comprobaron estas relaciones sin discrepancia en los
valores almacenados (epoch derivado en milisegundos):

```text
seconds_elapsed = (sensor_timestamp_ns - origin_monotonic_ns) / 1e9
epoch_ms_derived = origin_epoch_ms + trunc((sensor_timestamp_ns - origin_monotonic_ns) / 1e6)
```

GPS conserva ademas su epoch independiente. La diferencia GPS epoch menos epoch
derivado tiene mediana -15 ms y rango -108 a -11 ms. No se igualaron esos relojes
ni se corrigieron RAW. La correlacion en el mismo arranque debe usar la base
monotona compartida y las anclas de anotaciones.

## Conclusion y siguiente verificacion

La captura demuestra adquisicion y exportacion fisica de los cinco sensores y GPS
en una sesion corta de este telefono, con cierre y archivos consistentes. Es una
evidencia funcional positiva para A3, no validacion cientifica del monitoreo vial.
Las senales de movimiento pequenas y velocidad mediana nula son compatibles con
una prueba mayormente estacionaria; el montaje y contexto no se deducen del nombre.

Pendientes: una prueba con marca manual explicita (por ejemplo OTRO), ensayo de
permisos/rotacion, pantalla apagada, duracion prolongada y captura de recorrido con
montaje documentado. Las posiciones iniciales imprecisas y el hueco GPS deben quedar
visibles para el futuro adaptador/gate de calidad, sin inventar trayectorias o
asociaciones de eventos durante intervalos sin una referencia espacial adecuada.
