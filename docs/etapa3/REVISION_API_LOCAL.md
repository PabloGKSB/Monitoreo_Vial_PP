# Revision del primer incremento: API local

Fecha: **2026-10-09**. Evidencia EV-12. E3-04 verificada para su alcance local;
E3-01/E3-07/E3-10 parciales. No se modificaron RAW ni el proyecto Android.

## Implementacion comprobada

- [src/api.py](../../src/api.py): reutiliza lectores/calidad/GPS del V0;
  carga ZIP, calcula hash, inspecciona en trabajador local y sirve resultados/mapa.
- [run_api.py](../../run_api.py): arranque en 127.0.0.1, un proceso.
- [requirements-api.txt](../../requirements-api.txt): dependencias separadas
  para API y pruebas HTTP, sin imponerlas al flujo Streamlit existente.
- [Contrato](CONTRATO_API.md): formatos, relojes, estados, errores y limites.
- [tests/test_api.py](../../tests/test_api.py): 17 casos incluidos los
  parametrizados. Suite completa: **55 passed, 1 warning in 8.17s**, exit code 0.

Los casos cubren legado/nativo, trayectoria separada por huecos, valores ausentes,
marcas, errores estructurales/semanticos, limites, cola llena, estados pendientes,
reinicio e interrupcion. Una prueba concurrente comprueba lecturas durante 100
reemplazos del JSON de estado. La suite inicial detecto WinError 5 al reemplazar
un archivo abierto por un lector; un bloqueo local sincroniza estas operaciones.
Esta garantia corresponde a un proceso, no a varios servidores compartiendo datos.

La advertencia restante es deprecacion de httpx en Starlette TestClient; no es
un fallo de prueba. La compatibilidad de dependencias se revisara antes del
despliegue. No se declara rendimiento productivo ni validacion fisica a partir
de estos tests.

## ZIP real procesado por HTTP

Entrada: `data/raw/test_20260928_140148_062_anotaciones_imu_1790636845152.zip`.

SHA-256:
`be762e8966e00b0d6417adc0e0186cf1ee98fb87ab988cce2e8295623e914868`.

| Medida | Resultado |
|---|---:|
| Tamano ZIP | 17.497.742 bytes |
| Estado del trabajo | COMPLETED |
| Perfil de captura | capture-preview-2 |
| Duracion declarada/observada en reporte | 1.202,477 s |
| Registros de los cinco flujos inerciales mas GPS | 603.097 |
| Fijaciones GPS conservadas | 1.127 |
| Tramos GPS / polilineas en HTML | 2 / 2 |
| Distancia observada, sin unir el hueco | 7,494463 km |
| Anotaciones leidas | 2 |
| Calidad | WARNING |
| Descartes por cola declarados | 2.315 |
| Mayor hueco GPS | 74,528 s |
| Deteccion automatica | NOT_EVALUATED; event_count null |
| Carga hasta resultado/mapa, una ejecucion local | 1,225 s |

La ultima duracion incluye HTTP y consultas de esta ejecucion; no es una
comparacion antes/despues ni una medicion repetida de capacidad. Los huecos de
captura originales y los descartes siguen presentes. No se recuperaron muestras
ni se demuestra su causa. Dos anotaciones leidas no acreditan por si solas que
se realizo el ensayo de dos marcas y deshacer una.

Recibo estructurado local, excluido de Git:
`outputs/reports/api_local_20261009.json`. ZIP y resultados se conservan en
`.api_local/e3ff35ff-fd1e-4bc2-ba27-442f0a296ae5/`, tambien excluida de Git.

## Revision que podemos hacer ahora

1. Abrir http://127.0.0.1:8000/docs con el servidor activo. GET /health debe
   indicar local_inspection. POST /v1/jobs permite seleccionar otro ZIP.
2. Consultar estado y resultado del trabajo
   `e3ff35ff-fd1e-4bc2-ba27-442f0a296ae5`. Debe conservar WARNING y queue_dropped
   2315, dos anotaciones y NOT_EVALUATED. No confundir trabajo completado con
   datos perfectos ni con cero baches.
3. Abrir el [mapa local del ZIP](http://127.0.0.1:8000/v1/jobs/e3ff35ff-fd1e-4bc2-ba27-442f0a296ae5/map).
   El HTML contiene dos tramos; el intervalo GPS sin muestras no debe conectarse
   con una linea inventada. Requiere librerias/cartografia externas.
4. Preparar E3-02 en el telefono, con vehiculo detenido: iniciar sesion, marcar
   dos eventos, deshacer uno, finalizar y exportar. Registrar hora, version,
   dispositivo y acciones; pasar el ZIP para comprobar evento conservado, ID y
   relojes en V0/API. No realizar esta prueba operando la app como conductor.

**Validacion visual pendiente:** el navegador restringido no pudo descargar
Leaflet ni las otras librerias externas (ERR_NETWORK_ACCESS_DENIED). La revision
con red ampliada fue bloqueada por auto-review porque las teselas pueden revelar
al proveedor el area del recorrido. Se solicito autorizacion especifica antes
de repetirla. El resultado HTTP, GeoJSON y las dos polilineas en HTML estan
comprobados; no se afirma renderizado visual verificado mientras siga pendiente.

## Siguientes cierres

- E3-01/T-07: resolver preview frente al esquema de entrega y el ensayo fisico.
- E3-02/T-09: auditar captura nueva con marca/deshacer/exportacion.
- E3-03/T-10: politica general de rechazo de datos y huecos en deteccion.
- E3-05/T-16: PostgreSQL/PostGIS con migraciones y pruebas de integridad.
- E3-06/07: cuentas aisladas, trabajo durable e idempotencia antes de alojar.

El backlog queda en **5 V, 9 P, 4 N: 27,8 %** de las 18 tareas originales.
El incremento cambia T-17 de no evidenciada a parcial, pero no crea un cierre
completo adicional ni acredita el umbral del 50 %.
