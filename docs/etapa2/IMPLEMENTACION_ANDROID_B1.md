# Incremento B1: interfaz de monitoreo e historial local

Fecha: 2026-09-27. Proyecto: `C:/Users/GOMEPAB/AndroidStudioProjects/AnotadorVial`.
Referencia visual: propuesta de ocho pantallas compartida por Pablo. Se implementa
el flujo de captura disponible, no sus pantallas de deteccion automatica futura.

## Cambios observables

| Vista | Comportamiento implementado |
|---|---|
| Inicio | Nombre del recorrido, disponibilidad real del acelerometro/giroscopio, inicio y lista de recientes. |
| Recorrido activo | Tiempo, conteos, Hz medidos, errores, marcas recientes, anotacion mediante panel y confirmacion de fin. |
| Recorridos | Inventario de CSV de anotaciones guardados en Documents de la propia app, recuperable al reabrir. |
| Detalle | Fecha, duracion cuando existe FIN, marcas, metadatos/calidad IMU cuando existen y exportacion. |
| Eventos | Marcas manuales actuales e historicas; busqueda por tipo o recorrido y acceso a su sesion. |
| Ajustes | Tema claro/oscuro persistente, activacion de burbuja y permiso, datos de adquisicion de solo lectura. |

La navegacion inferior permanece disponible durante captura. Un aviso permite
volver al recorrido activo desde otras secciones. El boton de retroceso primero
cierra el detalle y luego vuelve a Inicio; salir de la pantalla no detiene sensores.
La burbuja es opcional: iniciar desde la app ya no requiere permiso de overlay.
El cambio de preferencia de burbuja no detiene el servicio IMU.

Se usan superficies claras, acento azul, verde para disponibilidad y advertencias
ambar/rojas. Tema oscuro consistente, iconos Material, controles con descripciones
accesibles, ayudas en iconos y pantallas desplazables. No se dibujan mapas,
trayectorias, senales, velocidades o predicciones ficticias.

## Arquitectura y alcance

- `ui/MonitoringApp.kt`: nueva entrada Compose, navegacion y vistas. Conserva los
  comandos compartidos con overlay: iniciar, anotar, deshacer y finalizar.
- `history/TripHistory.kt`: lectura de los CSV legacy con Apache Commons CSV;
  soporta campos entrecomillados, comas y saltos de linea sin usar split manual.
- `MainActivity.kt`: conecta la interfaz nueva y respeta la preferencia de burbuja.
  Impide deshacer una sesion finalizada o mientras se exporta.
- `OverlayService.kt`: actualiza el aviso final para hablar de captura propia.
- `capture/*`: reutilizado; no se altera el formato IMU ni se integran mas sensores
  en este incremento visual.

El historial es un indice de archivos existentes, no una nueva base Room. Una sesion
sin FIN sigue sin cierre confirmado; no se inventa una duracion. Un CSV ilegible
aparece con incidencia sin impedir consultar los demas. La lectura se ejecuta en
Dispatchers.IO y excluye el archivo de una captura activa o en proceso de cierre.
Los archivos historicos no se modifican ni eliminan.

La exportacion utiliza el escritor ZIP A2 para sesiones con carpeta IMU y comparte
CSV para sesiones antiguas de solo anotaciones. El detalle permite exportar solo
CSV tambien. Los metadatos inexistentes o ilegibles no se presentan como calidad
correcta. La exportacion incompleta puede fallar explicitamente si faltan metadatos.

Dependencias agregadas: `org.apache.commons:commons-csv:1.14.1` y
`androidx.compose.material:material-icons-core:1.7.8` (conjunto acotado de iconos).
Parser: [documentacion Apache Commons CSV](https://commons.apache.org/proper/commons-csv/apidocs/index.html).
Iconos: [documentacion Compose](https://developer.android.com/develop/ui/compose/graphics/images/material).
La biblioteca de iconos es legacy; no se adopto el paquete extendido completo.

## Evidencia y pruebas

- Respaldo anterior: `outputs/reports/AnotadorVial_pre_ui_20260927_195916.zip`.
- Parches en orden: `android_ui_b1.patch`, `android_ui_b1_screens.patch` y
  `android_ui_b1_review.patch`. Documentan cambios ya aplicados; no reaplicarlos.
- Compilacion del APK y 20 pruebas JVM aprobadas: cinco nuevas de historial,
  quince previas (incluida la prueba de ejemplo original).
- Compilacion de APK de pruebas instrumentadas con `MonitoringNavigationTest`.
  Compilar ese test NO equivale a ejecutarlo en el telefono.
- `lintDebug` ejecutado correctamente: cero errores y 30 advertencias en el proyecto
  (dependencias/versiones, recursos, accesibilidad de vistas e internacionalizacion,
  entre otras). No se afirma que el proyecto este libre de advertencias.
- El compilador advierte dos APIs Compose obsoletas usadas por la nueva UI
  (`LocalLifecycleOwner` y el posicionamiento de tooltip); siguen compilando con
  las dependencias actuales. Su migracion no se confunde con prueba funcional.
- No se instalo la version ni se ejecutaron capturas de pantalla en el dispositivo
  en este incremento. No habia un AVD configurado. Falta aceptacion visual y funcional.

## Aceptacion pendiente

1. Ejecutar Run en Android Studio, sin desinstalar la app ni borrar almacenamiento.
2. Comprobar las cuatro secciones, temas, retroceso y legibilidad en vertical,
   horizontal y con fuente ampliada. Revisar que la burbuja no oculte controles.
3. Comprobar que los recorridos anteriores siguen presentes y pueden compartirse.
4. Con el vehiculo detenido, crear `PRUEBA_UI`, registrar y deshacer una marca,
   navegar durante captura, finalizar y revisar conteos/metadatos del ZIP en PC.
5. Cerrar y reabrir la app despues del cierre; comprobar historial y detalle.
6. Probar errores de archivo, permisos de burbuja denegados y exportacion cancelada.

## Lo que no se declara terminado

GPS, gravedad, aceleracion lineal y rotacion siguen pendientes de integracion.
No hay detector, ML movil, mapa ni graficas de muestras recientes. La frecuencia
solicitada es fija; Ajustes no simula un control de frecuencia que no exista.
Tampoco hay recuperacion automatica de una grabacion tras muerte de proceso,
persistencia Room ni validacion de continuidad con pantalla apagada.

Este incremento reemplaza la afirmacion de A2 de que no existia historial visible:
ahora se consultan archivos persistentes, pero no se recupera la sesion activa.
No se crearon commits; el proyecto Android sigue pendiente de versionado Git.
