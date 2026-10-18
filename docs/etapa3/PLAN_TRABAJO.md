# Plan de trabajo hasta el 30 de octubre

Corte: 2026-10-09. Responsable: Pablo. Este plan inicia trabajo tecnico mientras
se espera la retroalimentacion de Etapa 2; la respuesta real puede ajustar
prioridades. Los objetivos de plataforma y validacion permanecen vinculados al
[backlog](BACKLOG.md), sin prometer detector validado ni continuidad sin perdidas.

## Secuencia de trabajo

| Periodo | Entregable previsto | Subtareas | Evidencia esperada |
|---|---|---|---|
| 09-15 octubre | Contrato de entrada, captura con marca, politica de calidad y API local minima; comenzar modelo central y diagnostico de captura. | E3-01 a E3-05, E3-12, E3-14, E3-21 | ZIP propio anotado leido, casos INVALID, carga/consulta local y mediciones iniciales. |
| 16-22 octubre | Usuarios, trabajos persistentes y despliegue; integrar historial/mapa y subida Android segun dependencias. Mejorar captura e iniciar inferencia continua. | E3-06 a E3-13, E3-15/16 | Dos cuentas aisladas, URL HTTPS, ZIP procesado, mediciones antes/despues y episodios candidatos. |
| 23-29 octubre | Congelar configuracion de evaluacion, realizar validacion integrada/terreno, corregir fallos y preparar informe/Git. | E3-17, E3-20, E3-21 | Metricas preliminares, errores y ajustes, criterios T actualizados y version reproducible. |
| 30 octubre | Entrega academica. | Evidencias de todos los bloques | Informe, demostracion y versiones identificadas. |

La primera semana acaba con una API local verificable; una URL desplegada con
usuarios y procesamiento depende de persistencia, autenticacion y cuenta del
proveedor. La compra del servicio y la publicacion son pasos posteriores a la
preparacion del codigo y configuracion.

## Proxima tarea concreta

Primer incremento del 09/10: **E3-04 verificada** y contrato local E3-01
documentado. API, estados, trayectoria, calidad y advertencias probados con ZIP
real; ver [revision local](REVISION_API_LOCAL.md). T-17 sigue parcial.

Siguiente comprobacion con Pablo: **E3-02**, con vehiculo detenido, dos marcas,
deshacer una, finalizar y exportar. Revisar ID, evento conservado y relojes tanto
en V0 como en API. Confirmar el alcance preview/entrega de E3-01 antes de cerrar
T-07/T-09; completar ficha E3-14.

Incremento del 10/10: **E3-03 verificada**, T-10 cerrada tecnicamente.
**E3-05/06 parciales:** modelo/migracion PostGIS y modo central con JWT Supabase
preparados; aislamiento probado con identidades sinteticas y SQLite. Siguiente
paso: configurar proyecto Supabase, ejecutar migracion y verificar el rol de
base/tokens de dos cuentas reales segun [la guia](INTEGRACION_SUPABASE.md).
Despues integrar cliente/login y subir APK. No publicar la demo sin cuentas.

Avance del 16/10 (**EV-15**): proyecto `monitoreo-vial` conectado; migraciones
0001/0002, PostGIS, restricciones y rol backend comprobados en Supabase. Configuracion
privada local con TLS verificado al pooler. Siete pruebas runtime con rollback y
arranque central 200/401 aprobados. El siguiente paso son dos cuentas Auth reales
y login/renovacion en cliente. E3-05/06 siguen parciales hasta completar su
validacion integrada; revisar TLS pooler-Postgres antes de desplegar.

Cierre posterior del 16/10 (**EV-16**): dos cuentas reales confirmadas por Pablo,
ZIP propio completo en ambas, aislamiento 404, renovacion y cierre; cliente
web probado en navegador. **E3-05/E3-06 verificadas y T-16 verificada**, con
7/18 tareas (38,9 %). E3-08 pasa a parcial por Docker/guardas/operacion preparados;
no hay servicio publicado. Siguiente: conectar Railway, resolver TLS upstream,
verificar imagen y restauracion; despues subir desde APK, aplazada por Pablo.

## Evidencia para los seis criterios

| Criterio de Etapa 3 | Peso | Trabajo asociado | Condicion verificable |
|---|---:|---|---|
| Incorporar retroalimentacion | 20 % | E3-22 y acciones que deriven | Correo y matriz comentario -> cambio -> prueba. Pendiente de recibir/registrar, sin atribuir mejoras internas al profesor. |
| Optimizar diseno | 15 % | E3-12/13 y mejoras medidas de procesamiento | Comparacion antes/despues bajo condiciones equivalentes; huecos/descartes y, si corresponde, memoria/tiempo. |
| Avance implementacion | 10 % | T-01 a T-18; ruta T-07/09/16 | Al menos 9 de 18 verificadas con criterios/evidencias; 6 al 10/10, desde 5 iniciales. HU completas visibles y cambios de alcance justificados. |
| Pruebas/resultados preliminares | 30 % | E3-02/03, E3-15 a E3-17 | Datos, protocolo, metricas y ajustes derivados. Distinguir software, ventanas y eventos; referencia revisada para FP/km. |
| Validacion preliminar | 10 % | E3-20 y ensayos de telefono | Flujo APK/ZIP -> servidor -> resultados -> mapa; fallos, acceso, carga y rendimiento controlados. |
| Documentacion | 15 % | E3-21 y este paquete | Diseno actualizado, ADR, limites, resultados, commits descriptivos y version de entrega. |

## Mediciones que deben prepararse

- Captura: duracion, conteos por sensor, frecuencia observada, intervalos/huecos,
  descartes por cola, estado de pantalla, montaje y bateria. Repetir el protocolo
  antes/despues de la mejora; no usar solo una frecuencia promedio.
- Servicio: tamano y hash del ZIP, entorno, duracion por fase, memoria maxima,
  resultado y errores. Probar al menos carga individual y dos cargas simultaneas;
  esto es una prueba inicial controlada, no capacidad productiva certificada.
- Permisos: usuario A no puede consultar/descargar/modificar datos de B; visitante
  solo ve puntos autorizados, sin ZIP, identidad ni recorrido completo.
- Detector: configuracion/modelo fijados antes de evaluacion reservada; ventanas
  continuas y episodios sin usar marcadores para localizarlos, matching uno-a-uno,
  precision/recall/F1 y FP/km sobre distancia evaluable. Publicar cobertura
  excluida por huecos y limites de referencias.

No se fijan umbrales de precision, latencia o continuidad a posteriori. Antes de
cada ensayo, registrar requisitos del protocolo y tolerancias de matching. Si
el resultado no los satisface, conservar la evidencia y planificar el ajuste.

## Revision semanal y contingencias

El 15 y 22/10 revisar evidencia y dependencias. Si la plataforma completa no cabe
en el plazo, demostrar el flujo integrado disponible, registrar pendientes y
preservar tiempo para pruebas e informe. No retirar T originales del denominador.
Una captura de pantalla o un healthcheck no cierra autenticacion o procesamiento.

Si el telefono no esta disponible, avanzar contrato/API/DB/quality y pruebas
sinteticas, manteniendo los ensayos fisicos pendientes. Si falta cuenta o
presupuesto, preparar despliegue reproducible y demostrar localmente; no declarar
alojamiento publico realizado. Las perdidas historicas no se pueden recuperar.

Registrar la retroalimentacion cuando llegue y valorar sus cambios de alcance.
Conservar compromisos OE1-OE6; modificar objetivos requiere decision documentada.
