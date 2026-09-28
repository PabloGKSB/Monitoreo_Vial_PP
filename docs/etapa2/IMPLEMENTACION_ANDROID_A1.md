# Incremento Android A1a: reloj y almacenamiento de anotaciones

Fecha: 2026-09-26. Implementado en el proyecto Android original, no en una copia.
Alcance acotado: comienzo de A1, no A1 completo ni captura IMU/GPS.

## Cambios

- session/SessionClock.kt: reloj inyectable para pruebas; conserva epoch real de
  marca y duracion monotona. Un salto del reloj civil no altera la duracion.
- storage/AnnotationCsvStore.kt: CSV UTF-8 con mismas cinco columnas; escape de
  comillas/comas; creacion exclusiva para evitar truncar una grabacion por colision.
- Deshacer prepara y sincroniza un snapshot temporal en el mismo directorio;
  reemplaza atomicamente el CSV al completar. Si preparar el snapshot falla,
  el original permanece intacto. Si el sistema no admite reemplazo atomico,
  falla la operacion en lugar de truncar el archivo original.
- MainActivity.kt delega en esos componentes. Conserva pantallas, overlay,
  funciones publicas, anotaciones manuales y compartir CSV.
- Dos nuevas clases de pruebas; no se anadieron dependencias ni permisos.

El append sigue siendo escritura directa de una anotacion; no se promete
recuperacion frente a interrupcion a mitad de append o fallo fisico. El estado
de sesion sigue en memoria y el I/O sigue sincronico. El fd.sync incrementa el
coste de escritura: NO reutilizar este escritor en callbacks de sensores a 100Hz.
El siguiente cambio debe introducir escritor serializado fuera de UI y estado
recuperable, con feedback de operacion pendiente/error para pantalla y overlay.

## Verificacion

Antes: gradlew testDebugUnitTest assembleDebug --offline exitoso; una prueba
de ejemplo. Despues: mismo comando exitoso, ocho pruebas, cero errores/fallos:
cinco de CSV, dos de reloj y una de ejemplo preexistente.

Los tests comprueban encabezado/append legacy, escape CSV, colision de archivo,
snapshot completo, fallo durante snapshot con conservacion byte a byte, salto
de reloj civil y origen independiente de sesiones.

APK: C:/Users/GOMEPAB/AndroidStudioProjects/AnotadorVial/app/build/outputs/apk/debug/app-debug.apk.
Reportes: app/build/reports/tests/testDebugUnitTest/index.html del proyecto Android.
No se instalo ni ejecuto en telefono; no hay prueba instrumentada de UI ni
garantia de comportamiento del almacenamiento Android a partir de tests en Windows.

Compilacion desde la carpeta Android, usando Java de Android Studio sin cambiar
variables globales del sistema:

```powershell
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
.\gradlew.bat testDebugUnitTest assembleDebug --offline
```

## Respaldo y trazabilidad

El proyecto Android no tenia repositorio Git al iniciar. No se inicializo ni
se realizo commit. Respaldo previo de src, configuracion de build y gradle:
outputs/reports/AnotadorVial_pre_captura_20260926_130113.zip en el proyecto Python.
SHA-256: 962FDEBD6D403C8BCCCCE105364723A8989D34C967E2BECF29EF1BB585450A6F.
No es una copia de datos privados del telefono ni de todas las caches de build.

[Patch aplicado](patches/android_incremento_a1.patch), conservado para revision
y versionado en este repositorio. Ya esta aplicado: no ejecutarlo nuevamente
ni usarlo para reemplazar cambios posteriores. No se modificaron RAW historicos.

## Siguiente comprobacion en Mi 10T

Con vehiculo detenido: iniciar, marcar dos eventos, deshacer uno, finalizar y
compartir. Comprobar CSV con inicio, evento conservado y fin; tiempos crecientes
en duracion, mismo encabezado y apertura en Python. Repetir desde overlay y
comprobar vuelta a pantalla. Resguardar exportaciones existentes antes de probar;
no desinstalar la app para instalar una actualizacion.

Este incremento aporta a T01/T09 y al contrato temporal, pero no cierra T02-07,
la recuperacion de sesion ni la validacion de adquisicion del plan A0-A5.
