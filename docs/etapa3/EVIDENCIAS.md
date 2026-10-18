# Evidencias de inicio de Etapa 3

Corte inicial: **2026-10-09**. Actualizacion de integracion: **2026-10-16**.
Este registro distingue inspeccion actual, resultados historicos y trabajo
planificado. No se modificaron RAW ni la APK durante esta
revision. Las rutas del proyecto Android son locales al equipo de Pablo.

## Fuentes verificadas

| ID | Fuente | Evidencia y limite |
|---|---|---|
| EV-01 | [Backlog heredado](../etapa2/BACKLOG.md), [contexto Etapa 2](../../CONTEXTO_ETAPA_2.md) | 26 HU, 18 T y 10 D; identificadores, titulos y vinculos de referencia. Estados fechados el 27/09; actualizar con fuentes posteriores. |
| EV-02 | [Android A1](../etapa2/IMPLEMENTACION_ANDROID_A1.md), [A2](../etapa2/IMPLEMENTACION_ANDROID_A2.md), [A3](../etapa2/IMPLEMENTACION_ANDROID_A3.md), [B1](../etapa2/IMPLEMENTACION_ANDROID_B1.md) | Implementacion, compilaciones y pruebas historicas. A3 registra 27 pruebas JVM y Lint sin errores. No se ejecuto Gradle en esta revision. |
| EV-03 | [Captura corta](../etapa2/REVISION_CAPTURA_PROPIA_20260927_204012.md) y [prolongada](../etapa2/REVISION_CAPTURA_PROPIA_20260928_140148.md) | Cinco flujos inerciales y GPS exportados. Prueba de 20 min: 603.097 muestras escritas, 2.315 descartes y huecos; no acredita continuidad sin perdidas. |
| EV-04 | [Adaptador](../etapa2/ADAPTADOR_NATIVO_V0.md), [codigo](../../src/native_loader.py), [pruebas](../../tests/test_native_loader.py), [analizador](../../src/analyzer.py) | capture-preview-2 selecciona inspeccion nativa: relojes, sensores separados, GPS, calidad y marcas. Las detecciones automaticas nativas no estan habilitadas. |
| EV-05 | [Campana local](../CAMPANA_PILOTO_2026_09_25.md), [revision](../REVISION_CAMPANA_2026_09_26.md), [retraso](../PRUEBA_RETRASO_2_5_SEGUNDOS.md), [dataset](../../src/pilot/dataset.py), [evaluacion](../../src/pilot/evaluation.py), [pruebas](../../tests/test_pilot.py) | Features y comparacion umbral/RF ejecutadas; LOCO agrupa ida/vuelta y aplica purga. Etiquetas normales candidatas, marcas retrospectivas y montaje confundido con ruta limitan conclusiones. |
| EV-06 | [RoadSens](../etapa2/EXPERIMENTO_ROADSENS4M.md), [codigo](../../src/pilot/roadsens.py), [pruebas](../../tests/test_roadsens.py) | Auditoria, ventanas, folds por archivo y transferencia implementados. RF externo F1 macro 0,695; transferencia local precision BACHE 0,299, F1 0,458. No es validacion de deteccion continua. |
| EV-07 | [Calidad](../../src/quality.py), [GPS](../../src/gps.py), [mapas](../../src/maps.py), [app](../../app.py) | Reportes y mapa locales; huecos GPS separan polilineas. Falta bloqueo general por calidad INVALID y mapa alimentado por endpoints centrales. |
| EV-08 | [Informe de Etapa 2](../etapa2/entrega/Informe_Etapa2_Monitoreo_Vial_Pablo_Gomez.docx), [registro de entrega](../etapa2/entrega/LEEME_ENTREGA.md) | Ocho capturas reales de distintas sesiones y vista logica nativa. Evidencia visual; no sustituye prueba integrada de nueva marca, deshacer y lectura de ZIP. Pablo informo envio el 02/10. |
| EV-09 | [run_tests.py](../../run_tests.py) y [tests](../../tests) | Ejecucion del 09/10: **38 passed in 12.74s**, exit code 0. No reentrena modelos ni repite campanas fisicas. |
| EV-10 | Inspeccion local de Git y archivos, 09/10, previa al incremento API | Cambios de V0 y archivos nativos/RoadSens aun modificados o sin seguimiento. En ese corte inicial no habia API; EV-12 registra su implementacion posterior. Migraciones centrales y despliegue siguen pendientes. No se hizo commit ni push. |
| EV-11 | Fuente Android actual inspeccionada, 09/10 | Proyecto y modulos presentes; SensorManager registra sensores; GPS usa LocationManager; escritor usa ArrayBlockingQueue y cuenta offer fallidos. FusedLocationProviderClient y Room no se acreditan. |
| EV-12 | [API](../../src/api.py), [pruebas](../../tests/test_api.py), [contrato](CONTRATO_API.md), [revision](REVISION_API_LOCAL.md) | Carga ZIP, trabajo local acotado, estados/resultados, mapa y errores implementados; ZIP real del 28/09 inspeccionado. Ver resultados reproducibles y limites en la revision. Sin usuarios, base central, despliegue ni detector. |
| EV-13 | [Politica](POLITICA_CALIDAD.md), [codigo](../../src/processing_policy.py), [pruebas](../../tests/test_processing_policy.py), [estados UI](../../tests/test_app_quality.py) | INVALID bloquea procesamiento/deteccion; bloques y ventanas no cruzan huecos, falta de observaciones no se presenta como BUENO y no evaluado no es cero. ZIP real mantiene avisos. T-10 verificada tecnicamente, no detector validado. |
| EV-14 | [Integracion](INTEGRACION_SUPABASE.md), [autenticacion](../../src/auth.py), [repositorio](../../src/database.py), [API central](../../src/central_api.py), [migracion](../../migrations/versions/0001_central.py) | Supabase JWT, consultas privadas, historial y persistencia probados con tokens EC sinteticos y SQLite. Revision PostgreSQL compila y prueba PostGIS real queda omitida. Suite: 87 passed, 1 skipped, 1 warning in 6.72s. No conexion ni cuentas Supabase reales, despliegue o cambio Android. |
| EV-15 | [Conexion real y limites](INTEGRACION_SUPABASE.md), [rol backend](../../migrations/versions/0002_backend_role.py), [pruebas runtime](../../tests/test_backend_postgres_live.py) | 16/10: proyecto monitoreo-vial conectado, revisiones 0001/0002 aplicadas, PostGIS/RLS/FK comprobados, rol sin BYPASSRLS y TLS cliente-pooler verify-full. Siete pruebas runtime aprobadas con rollback y arranque central 200/401. Cero cuentas Auth; login real y TLS pooler-Postgres pendientes. Sin despliegue ni cambios Android. |
| EV-16 | [Validacion de cuentas/cliente](VALIDACION_CUENTAS_CLIENTE.md), [cliente](../../web/client.js), [prueba integrada](../../scripts/validate_accounts.py), [despliegue preparado](../../deploy/README.md) | 16/10: dos correos confirmados por Pablo, dos cuentas con ZIP real completado, mapas/resultados/originales y ocho accesos cruzados 404. Renovacion y cierre reales; cliente probado en Edge sin errores JS o tokens persistentes. 106 pruebas Python aprobadas y siete JS. Respaldo local verificado y retencion simulada. Docker sin ejecutar; Railway, TLS upstream, respaldo externo/restauracion y APK pendientes. |

Proyecto Android:
`C:/Users/GOMEPAB/AndroidStudioProjects/AnotadorVial`.
Archivos comprobados bajo `app/src/main/java/com/monitoreovial/anotador/`:
`MainActivity.kt`, `OverlayService.kt`, `ui/MonitoringApp.kt`,
`session/SessionClock.kt`, `storage/AnnotationCsvStore.kt`,
`capture/RecordingService.kt`, `capture/ImuSessionWriter.kt`,
`capture/GpsCollector.kt`, `capture/ImuArchive.kt` e `history/TripHistory.kt`.

## Verificacion reproducible

Desde la raiz del V0:

```powershell
.\.venv\Scripts\python.exe run_tests.py
git status --short
```

Los informes de campanas identifican sus entradas y ejecuciones. Los RAW y
outputs pueden estar excluidos de Git; conservar sus hashes y el paquete
experimental para reproducirlos sin publicar trayectorias privadas.

## Restricciones del corte

- La captura prolongada tiene huecos y descartes. Su causa no esta aislada.
- La lectura nativa esta resuelta para inspeccion; no equivale a un detector
  nativo validado ni al contrato V1 completo.
- Los tests de software no miden error GPS real, bateria o repetibilidad fisica.
- Los experimentos por ventanas no ofrecen FP/km ni matching de episodios.
- No se verificaron proveedor, plan contratado, URL desplegada o sincronizacion
  con GitHub. Railway es una alternativa planificada, sin compra o despliegue.

## Retroalimentacion de Etapa 2

Ultimo dato comunicado: el 02/10 Pablo habia enviado Etapa 2 y aun no tenia
retroalimentacion. Al corte del 09/10 no se ha aportado una respuesta posterior.

| ID | Comentario y origen | Fecha | Cambio asociado | Evidencia de comprobacion | Estado |
|---|---|---|---|---|---|
| FB-01 | Pendiente de recibir/registrar | Pendiente | Se definira a partir del comentario real | Correo original y resultado de la accion | PENDIENTE |

Cuando llegue: registrar el texto o una sintesis fiel, desglosar observaciones
accionables y enlazar sus subtareas y pruebas. Si no hay correcciones, registrar
esa circunstancia con el correo; no inventar cambios pedidos por el profesor.
