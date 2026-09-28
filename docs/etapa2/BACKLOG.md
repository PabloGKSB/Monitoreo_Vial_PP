# Backlog trazable de Etapa 2

Fecha: 2026-09-26. Fuente: Etapa 1 pp. 31-35; los ID, prioridades y puntos
originales se conservan. Titulos abreviados, no nuevas historias sustitutas.
Revision de coherencia: 2026-09-27, contrastada directamente con PDF y codigo.
Hallazgos y criterios pendientes: [revision de cierre](REVISION_CIERRE_ETAPA2.md).
Responsable propuesto: Pablo; revision academica con profesor guia.

Estados de implementacion: I = existe evidencia local de implementacion;
P = parcial o solo experimental; N = no evidenciado en el alcance inspeccionado.
I NO significa aceptacion completa de la HU. La columna pendiente indica que
falta antes de cerrarla. Validacion cientifica no se deduce de tests unitarios.

Evidencias: E1 [V0](../../src/analyzer.py); E2 [loader](../../src/loader.py),
[calidad](../../src/quality.py) y [GPS](../../src/gps.py);
E3 [piloto](../../src/pilot/__main__.py) y [evaluacion](../../src/pilot/evaluation.py);
E4 [pruebas](../../tests/test_pilot.py); E5 [campana](../CAMPANA_PILOTO_2026_09_25.md);
E6 [sensibilidad temporal](../PRUEBA_RETRASO_2_5_SEGUNDOS.md);
E7 AnotadorVial, MainActivity.kt/OverlayService.kt en AndroidStudioProjects
(inspeccion de fuente, sin nueva prueba de dispositivo);
E8 [interfaz V0](../../app.py);
E9 [incremento Android A2](IMPLEMENTACION_ANDROID_A2.md), implementado el 27/09,
compilacion y pruebas JVM; sin aceptacion fisica todavia;
E10 [interfaz Android B1](IMPLEMENTACION_ANDROID_B1.md), historial local de archivos,
navegacion y exportacion historica; pruebas JVM, aceptacion visual pendiente;
E11 [sensores y GPS A3](IMPLEMENTACION_ANDROID_A3.md), cinco sensores y GPS propios,
permisos y capture-preview-2; aceptacion completa y adaptador Python pendientes;
E12 [captura propia real](REVISION_CAPTURA_PROPIA_20260927_204012.md), cinco sensores,
GPS y exportacion auditados en 88.833 s; sin marcas manuales ni ensayo prolongado.
E9-E11 describen el estado de sus incrementos; E12 agrega evidencia fisica posterior.
Disenos: DT [tecnico](DISENO_TECNICO.md), CD [contrato](CONTRATO_DATOS.md),
PE [protocolo](PROTOCOLO_EXPERIMENTAL.md). Todos en borrador, no aprobados.

## 1. Historias originales y brechas

| HU | EP | Prior./pts | OE / requisitos | Elemento | Impl. y evidencia | Pendiente de aceptacion |
|---|---|---|---|---|---|---|
| HU-01 | EP-01 | Alta/5 | OE1; RNF10 | Arquitectura/modelo | P; DT/CD, diagramas previos | Revisar modelo y contratos; actualizar diagramas. |
| HU-02 | EP-02 | Alta/3 | OE2; RF01-02 | Inicio/fin captura | I; E9/E12 INICIO/FIN, drenado y exportacion reales | Revisar unicidad local y aceptacion de flujo; no agregar Room como criterio original de HU02. |
| HU-03 | EP-02 | Alta/8 | OE2; RF03-05/07 | Captura IMU | I; E11/E12 cinco flujos reales, aprox. 102.9 Hz | Ensayo prolongado/pantalla apagada y alcance de deteccion de perdidas. |
| HU-04 | EP-02 | Alta/5 | OE2; RF06/07 | Captura GPS | I; E11/E12 64 fijaciones, tiempos, precision y velocidad | Denegacion/ausencia de fijacion y continuidad; accuracy no es error espacial medido. |
| HU-05 | EP-02 | Alta/3 | OE2; RNF03 | Estado captura | P; E9/E10 conteos, Hz, descartes, errores y navegacion | Aceptacion de UI y continuidad fisica. |
| HU-06 | EP-03 | Alta/5 | OE2; RF11, RNF08 | Persistencia local | P; E9/E10/E12 archivos locales reales e historial | Aceptar desviacion T05/Room y politica de recuperacion; prueba de interrupcion. |
| HU-07 | EP-03 | Alta/5 | OE2/4; RF12 | Exportar RAW | P; E11/E12 ZIP propio recibido y auditado en PC | R-01: lector legacy lo interpreta parcialmente mal; falta adaptador validado y contrato. |
| HU-08 | EP-04 | Alta/3 | OE3; RF08-09, RE01-03 | Metadatos captura | P; E5 y ficha propuesta | Completar vehiculo/dispositivo/versiones sin inventar datos. |
| HU-09 | EP-04 | Alta/3 | OE3; RF10 | Marcas de referencia | I; E7 y CSV reales | Congelar semantica retrospectiva, prueba de fallo/deshacer e impacto haptico. |
| HU-10 | EP-05 | Alta/5 | OE4; RF13-14 | Calidad temporal | I; E2/E3 | Gate INVALID general y tests de todos los casos RAW. |
| HU-11 | EP-05 | Alta/3 | OE4; RF15 | Calidad GPS | I; E2 | Validar limites de precision y evidencia espacial externa. |
| HU-12 | EP-06 | Alta/5 | OE4; RF16-17 | Preprocesamiento | I V0; E1 | Comparacion controlada de filtros/marco; piloto nativo es otra rama. |
| HU-13 | EP-06 | Alta/5 | OE4; RF18-19 | Features | I; E1/E3/E4 | Diccionario versionado y cobertura de casos limite. |
| HU-14 | EP-07 | Alta/5 | OE4; RF20 | Baseline interpretable | I V0; E1 | Evaluacion continua con referencias; no sustituirlo por umbral supervisado. |
| HU-15 | EP-07 | Alta/5 | OE4; RE11 | Sensibilidad | P; E6 | Estudio planificado de parametros V0, no solo retraso piloto. |
| HU-16 | EP-07 | Alta/8 | OE3/4; RF21, RE06-08 | Dataset etiquetado | P; E3/E5 | Verdad de terreno/revisiones independientes; NORMAL sigue candidato. |
| HU-17 | EP-07 | Media/8 | OE4/6; RF21/30 | Evaluacion ML | P; E3/E4/E6 | Metricas por ambas clases y evaluacion independiente; no declarar generalizacion. |
| HU-18 | EP-08 | Alta/5 | OE4/5; RF22 | Asociacion GPS | I; E2 | Medir error espacial con referencia externa. |
| HU-19 | EP-10 | Alta/5 | OE5; RF26-27 | Mapa | I V0; E8 | Prueba de interfaz y paquete de evidencia de entrega. |
| HU-20 | EP-09 | Media/8 | OE5; RF24 | Persistencia central | N; DT propuesto | DDL, migracion y consultas; planificar extension sin borrar OE5. |
| HU-21 | EP-09 | Media/5 | OE5; RF25 | API | N; DT propuesto | OpenAPI, autenticacion, implementacion y pruebas. |
| HU-22 | EP-10 | Media/5 | OE5; RF28 | Filtros | P; E8 seleccion local | Filtros fecha/categoria y datos centrales segun alcance acordado. |
| HU-23 | EP-11 | Alta/5 | OE6; RF29 | Precision/Recall/F1 | P; E3 | Matching de eventos y referencias validas; cifras actuales son ventanas. |
| HU-24 | EP-11 | Alta/3 | OE6; RF29 | FP/km | N | Detector continuo y referencia de recorrido completo; no usar negativos muestreados. |
| HU-25 | EP-11 | Alta/5 | OE6; RF30, RE04 | Repetibilidad | N evaluacion controlada; PE | Pasadas mismo sentido/condiciones e identidad de defectos revisada. |
| HU-26 | EP-11 | Media/8 | OE6; RE05/12 | Robustez | P diagnostico E5/E6 | Experimento controlado; montaje y ruta actuales estan confundidos. |

Los 26 elementos permanecen en el inventario, incluidas las extensiones. No se
consideran cerradas HU16/17/23 por disponer de un CSV con etiquetas o de F1.

## 2. Tareas originales

| T | HU original | Tarea | Estado actual y evidencia / pendiente |
|---|---|---|---|
| T-01 | HU-02 | Proyecto Android y modulos | E11/B1: UI, servicio, capture, storage, session e history implementados; sin cierre global de arquitectura. |
| T-02 | HU-03 | SensorManager | E11/E12 implementado y demostrado en prueba corta; estabilidad prolongada pendiente. |
| T-03 | HU-04 | FusedLocationProviderClient | E11/E12 GPS con LocationManager demostrado; Fused no implementado, desviacion por aceptar. |
| T-04 | HU-02/03/04 | Foreground Service captura | Parcial E11 IMU/GPS con tipos foreground; aceptacion de continuidad pendiente. |
| T-05 | HU-06 | Room y DAOs | Modelo DT; implementacion pendiente. |
| T-06 | HU-06 | Escritura por lotes | E9/E12 cola/escritor buffered, JVM y archivos reales; sin Room, ensayo de fallo/carga pendiente. |
| T-07 | HU-07 | Esquema exportacion | E11 capture-preview-2 ejecutable; no equivale al contrato V1 completo CD. |
| T-08 | HU-08 | Montaje y ficha | Borrador PE/ficha; completar datos y revisar antes de nueva campana. |
| T-09 | HU-09/16 | Anotacion | E7/CSV legacy y tests JVM; E12 no incluye marcas: prueba integrada de marca/deshacer pendiente. |
| T-10 | HU-10/11 | Refinar QualityReport | E2/E3; gate INVALID y auditoria V0 pendientes. |
| T-11 | HU-15 | Sensibilidad V0 | E6 solo piloto; no cerrar tarea completa. |
| T-12 | HU-23 | Matching uno-a-uno | Diseno DT; implementacion pendiente. |
| T-13 | HU-16 | Dataset features | E3/E4; etiquetas pendientes de validacion. |
| T-14 | HU-17 | Split grupos | E3/E4 LOCO y purga implementados; ver limites de muestra. |
| T-15 | HU-17 | Baseline supervisado | Umbral y RF E3; evaluacion exploratoria, no detector validado. |
| T-16 | HU-20 | PostgreSQL/PostGIS | Modelo logico DT; DDL/migraciones pendientes. |
| T-17 | HU-21 | FastAPI | Boceto DT; implementacion pendiente. |
| T-18 | HU-19/22 | Mapa con endpoints | Mapa local E8; integracion remota pendiente. |

## 3. Subtareas de diseno propuestas (no sustituyen HU/T)

Linea base propuesta el 26/09, posterior al backlog original; debe revisarse con
Pablo. No afirmar que este denominador estaba acordado en Etapa 1. No hay
porcentaje de avance aprobado hasta que se acepte el conjunto y sus criterios.
Diseno documentado no equivale a revisado/cerrado. No se asignan retrospectivamente
fechas de cierre. Esta separacion evita declarar 100 % por haber creado documentos.

| ID | Padre | Evidencia | Criterio para cierre del diseno | Estado |
|---|---|---|---|---|
| D-01 | HU01 | DT seccion 1 / revision de cierre | Limites actual/futuro revisados y diagrama actualizado, incluido piloto. | Texto actualizado; diagrama y aceptacion pendientes |
| D-02 | HU01/06/20, T05/16 | DT seccion 2 | Entidades, cardinalidades, claves y ejemplo de integridad revisados. | Borrador |
| D-03 | HU07, T07 | CD / E12 / R-01 | Campos/unidades/versionado y paquete ejemplo validados contra esquema. | Ejemplo preview auditado; contrato/mapeo PC pendiente |
| D-04 | HU12/18 | CD seccion 2 / E12 / R-01 | Reglas epoch/monotono, fallos y casos de prueba revisados. | Anclas auditadas; lector PC incompatible y casos limite pendientes |
| D-05 | HU02-06, T01-06 | DT F-02/F-02a | Estados/transiciones/errores/permisos y persistencia recuperable revisados. | Flujo actual descrito; recuperacion y aceptacion pendientes |
| D-06 | HU10-15/18, T10-11 | DT F-03, CD | Gates de calidad, parametros y salidas trazables especificados y revisados. | Borrador |
| D-07 | HU08-09/16/25, T08-09 | PE y ficha | Protocolo operable, rubrica y registro de incertidumbre aceptados. | Borrador; datos por completar |
| D-08 | HU17/23-26, T12-15 | PE, DT F-04 | Separacion por hipotesis, matching y metricas definidas sin fuga. | Borrador |
| D-09 | HU20-22, T16-18 | DT seccion 5 | Alcance extension acordado; diseno de consultas, acceso y contrato API. | Parcial; OpenAPI pendiente |
| D-10 | HU01, RNF12-13 | DT ADR, este backlog | Trazabilidad completa, privacidad, decisiones y revision de evidencias. | Borrador |

Formula cuando la linea base sea aceptada: numero D cerradas con evidencia /
total D comprometidas de diseno * 100. Mostrar al lado el inventario entero de
26 HU/18 T; no usar esta formula como porcentaje de implementacion del proyecto.
Los cambios de alcance deben tener motivo, fecha y aprobador; no eliminar D
pendientes para inflar avance.

## 4. Cobertura adicional de requisitos

| Requisitos Etapa 1 | Diseno / HU | Evidencia o brecha |
|---|---|---|
| RNF01-04 | D05, HU02-05/09 | Android nativo/overlay parcial; continuidad sensores pendiente. |
| RNF05-07 | D03-04/06 | RAW/epoch/provenance piloto; historial V0 pendiente. |
| RNF08 | D05 | E9 cola acotada implementada; capacidad y continuidad por aceptar en dispositivo. |
| RNF10-12 | D01/10 | Modulos y tests; falta cobertura unitaria especifica de todos los modulos y commits recientes. |
| RNF13-16 | D09-10/06 | Acceso/retencion pendientes; config parametrizada y logica fuera de UI existentes. |
| RD01-22 | D02-04/07 | Modelo/contrato/ficha; metadatos de sensor, vehiculo y evidencia por completar. |
| RE01-08 | D07 | Montaje, sesiones, repeticiones, etiquetas y evidencia. |
| RE09-12 | D08 | Grupos, holdout, sensibilidad y condiciones no comparables. |
| RE13 (antes RNF09) | D07 | Bateria/almacenamiento: registrar en futura captura; no medidos actualmente. |

## 5. Orden de cierre propuesto

1. Revisar D01-04 con archivos de ejemplo y alinear arquitectura vigente con piloto.
2. Revisar D05-08 con Pablo, completar ficha y ejecutar simulacion de sesion.
3. Acordar D09/OE5, detallar interfaces y completar D10 con evidencias.
4. Registrar revisiones, criterios satisfechos y bloqueos concretos antes de calcular avance.

No se fija nota esperada ni se interpreta la nota 7.0 de Etapa 1 como aprobacion
de este nuevo diseno. El informe de Etapa 2 y los commits son trabajos separados.
