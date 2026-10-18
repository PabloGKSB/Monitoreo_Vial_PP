# Etapa 3: mejoras, pruebas y validacion preliminar

Inicio de la revision: 2026-10-09. Entrega: **2026-10-30**, segun Pablo.
Responsable del proyecto: Pablo Javier Gomez Quidel.

| Documento | Uso |
|---|---|
| [Backlog](BACKLOG.md) | Inventario de 26 HU y 18 T, criterios de cierre, porcentaje de implementacion y subtareas de Etapa 3. |
| [Evidencias](EVIDENCIAS.md) | Fuentes inspeccionadas, pruebas y limitaciones que sustentan los estados. |
| [Plan de trabajo](PLAN_TRABAJO.md) | Prioridades, dependencias, fechas y evidencias para los seis criterios de la rubrica. |
| [Contrato de API](CONTRATO_API.md) | Perfiles ZIP, relojes, endpoints, estados, limites y ejecucion local. |
| [Revision de API local](REVISION_API_LOCAL.md) | Resultado del ZIP real, comprobaciones y siguientes pasos de revision. |
| [Politica de calidad](POLITICA_CALIDAD.md) | Bloqueo INVALID, continuidad, cobertura GPS y significado de no evaluado. |
| [Integracion Supabase](INTEGRACION_SUPABASE.md) | Conexion real del 16/10, migraciones PostGIS, rol backend, JWT, permisos y limites de validacion. |
| [Cuentas y cliente web](VALIDACION_CUENTAS_CLIENTE.md) | Dos cuentas confirmadas, prueba ZIP integrada, navegador, cuotas, respaldo y limites de despliegue. |
| [Contexto inicial](CONTEXTO_ETAPA_3.md) | Nota historica del 28/09; su tabla de proveedores y pendientes no es una evaluacion actual. |

El corte del 10/10 reconoce 6 tareas con implementacion tecnica verificada,
9 parciales y 3 pendientes: **6/18 = 33,3 %**. El umbral de referencia del
50 % requiere 9 tareas verificadas. Este recuento local usa las tareas originales
de [Etapa 2](../etapa2/BACKLOG.md), heredadas de Etapa 1, y criterios operativos
explicitos. No es una calificacion academica ni aceptacion completa de las HU.

La retroalimentacion de Etapa 2 no ha sido compartida al corte. Su registro
permanece pendiente. Las mejoras internas no se atribuyen al profesor.

El primer incremento implementa la API local de inspeccion y mapa, accesible en
el puerto configurado (8000 por defecto; revision del 10/10 en 8001) mientras
el servidor este activo. E3-03/E3-04 estan verificadas. Desde el 16/10,
`monitoreo-vial` esta conectado: migraciones, PostGIS, rol backend y operaciones
del repositorio comprobados en la instancia real con rollback (EV-15).
Cuentas Auth y cliente web quedaron verificados en EV-16 con dos identidades
reales y ZIP propio. T-16 pasa a verificada: **7/18 = 38,9 %**, ocho parciales y
tres pendientes. T-17 sigue parcial por despliegue, idempotencia y cola durable.
La preparacion HTTPS esta disponible; Railway no esta conectado, TLS upstream
y restauracion siguen pendientes. APK y detector nativo no cambian.
