# Contexto de traspaso: Etapa 2

Actualizado: 11 de septiembre de 2026.
Entrega limite confirmada por Pablo: **viernes 2 de octubre de 2026**,
informe y avance. Este documento permite continuar en un chat nuevo usando
la misma carpeta. Es una referencia de trabajo, no una aprobacion del profesor.

## 1. Proyecto y fuentes

- Estudiante: Pablo Javier Gomez Quidel, Ingenieria en Informatica, UCT.
- Profesor guia: Luis Alberto Caro Saldivia.
- Titulo del informe: Sistema de Sensado Movil de Bajo Costo para la Deteccion
  y Clasificacion Georreferenciada de Irregularidades Viales mediante
  Smartphones y Aprendizaje Automatico.
- Carpeta: `C:\Users\GOMEPAB\Desktop\Protipo V0`.
- Informe entregado, 41 paginas:
  `C:\Users\GOMEPAB\Downloads\Informe_Etapa1_Monitoreo_Vial_PP_Pablo_Gomez.pdf`.
- Repositorio citado en el informe:
  https://github.com/PabloGKSB/Monitoreo_Vial_PP
- Documentacion local: [README.md](README.md) y
  [DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md).
- Diagrama actual generado con Archify:
  [arquitectura-v0.html](docs/arquitectura-v0.html).
  Fuente editable: [arquitectura-v0.json](docs/arquitectura-v0.json).
  [Registro de validacion](docs/arquitectura-v0-validacion.md).

La lectura anterior del PDF reviso su contenido textual; no constituyo una
auditoria de sus referencias bibliograficas ni una revision visual completa.
Reconsultar el PDF para transcribir requisitos o citas exactas.

## 2. Retroalimentacion recibida

Pablo compartio la respuesta del profesor: "Tienes la nota 7.0 en Etapa 1.
Muy buen informe." La fecha exacta del correo no fue indicada.
Estado: **retroalimentacion recibida, positiva y sin correcciones especificas**.
Conservar el correo como evidencia. La nota no implica aprobacion explicita
de cada decision futura ni acredita cambios incorporados.
No atribuir al profesor las observaciones tecnicas del asistente.
Registrar en la matriz el comentario, origen, fecha cuando se confirme y
que no se solicitaron cambios especificos.

## 3. Rubrica de Etapa 2 proporcionada por Pablo

| Criterio | Peso | Evidencias que deben prepararse |
|---|---:|---|
| Incorporar retroalimentacion | 20 % | Cambios especificos en diseno, tecnica y planificacion vinculados a observaciones reales. |
| Avance del diseno | 10 % | Registro actualizado de tareas de diseno frente al backlog completo; demostrar el 100 % de esas tareas. |
| Calidad del diseno | 55 % | Diagramas con convenciones reconocidas, decisiones tecnicas justificadas y adecuacion a objetivos y requisitos. |
| Documentacion | 15 % | Disenos, cambios, decisiones, desviaciones justificadas y repositorio Git con commits descriptivos. |

El 100 % solicitado se refiere a las tareas de diseno definidas en el backlog,
no a terminar toda la implementacion. Establecer su conjunto y criterios de
terminado antes de calcular avance; no reducirlo retrospectivamente para
aparentar cumplimiento.

## 4. Compromisos de Etapa 1

Objetivo general: disenar e implementar un sistema Android de adquisicion,
almacenamiento, procesamiento, deteccion/clasificacion y visualizacion
georreferenciada, evaluado mediante recorridos controlados en Temuco.

Los objetivos especificos, resumidos de las paginas 11-12, son:

- OE1: arquitectura, requisitos, datos e interfaces.
- OE2: APK Kotlin con sensores, ubicacion, persistencia local y exportacion/sincronizacion.
- OE3: protocolo reproducible de captura, etiquetado y evidencia de terreno.
- OE4: pipeline reproducible y comparacion del baseline con ML.
- OE5: almacenamiento central, servicios y visualizacion geoespacial.
- OE6: validacion de deteccion, calidad temporal, error espacial, repetibilidad y robustez.

El informe contiene 26 historias HU-01 a HU-26, epicas EP-01 a EP-11 y tareas
T-01 a T-18 (paginas 31-35). Conservar esos identificadores y desglosarlos;
no crear un backlog desconectado de los objetivos y requisitos existentes.
El Anexo A (pagina 41) contiene ejemplos de trazabilidad, no la matriz completa.

Tecnologias propuestas en el informe: Kotlin, Compose, SensorManager,
FusedLocationProviderClient, Foreground Service, Coroutines/Flow y Room/SQLite
para Android; Python para procesamiento; FastAPI y PostgreSQL/PostGIS para
la plataforma central. TypeScript/Leaflet/Plotly para la futura interfaz;
React es opcional. Son propuestas del informe, no componentes ya implementados.

## 5. Estado del V0

Aplicacion offline Python con Streamlit. `TripAnalyzer` es la fachada reutilizable:

```text
ZIP -> carga y calidad -> senal -> ventanas -> detector -> GPS -> segmentos
                                                                  |
                                             AnalysisResult -> Streamlit
                                             exportacion -> CSV / JSON
                                             maps.py -> mapa HTML
```

| Archivos | Responsabilidad implementada |
|---|---|
| app.py | Seleccion/subida de ZIP, parametros, resumen, calidad, eventos, mapa y graficos. |
| src/loader.py, src/utils.py | Lectura de CSV dentro de ZIP, normalizacion y manejo de tiempos. |
| src/quality.py | Duracion, frecuencia tipica, cortes y comprobaciones GPS. |
| src/preprocessing.py | Magnitud, estimacion heuristica de gravedad, suavizado y jerk. |
| src/features.py, src/detector.py | Ventanas, caracteristicas, score robusto y agrupacion temporal. |
| src/gps.py | Asociacion temporal, velocidad y distancia. |
| src/segmentation.py, src/scoring.py | Agregacion espacial e indice vial experimental. |
| src/analyzer.py, src/config.py | Coordinacion, parametros y exportacion. |
| src/annotations.py | Carga de etiquetas y matching exploratorio; aun sin interfaz integrada. |
| src/maps.py | Folium con OpenStreetMap. |
| tests/ | Pruebas sinteticas de modulos y del recorrido completo. |

Los ZIP originales de Claro Solar y Monte Oscuro estan en `Data/`; tambien
se admite `data/raw/`. Windows no distingue mayusculas en estas rutas.
Las cargas manuales se guardan en `data/processed/uploads/`.
Resultados en `outputs/events`, `outputs/reports` y `outputs/maps`.

Ultimos resultados reportados en sesiones anteriores, NO recalculados en este traspaso:

| Recorrido | Distancia | Velocidad media | Eventos candidatos |
|---|---:|---:|---:|
| Claro Solar | 6.03 km | 18.0 km/h | 7 |
| Monte Oscuro | 8.59 km | 27.5 km/h | 3 |

La ultima ejecucion reportada de pytest aprobo 12 pruebas. No equivale a
validacion cientifica. Volver a ejecutar al establecer la linea base de Etapa 2.
Las categorias LEVE/MEDIA/ALTA y BUENO/REGULAR/MALO son experimentales.

El fondo CARTO se reemplazo por OpenStreetMap al aparecer API KEY REQUIRED.
El HTML cartografico necesita Internet para sus teselas.
Archify esta instalado como skill y el diagrama actual paso 9 comprobaciones
y revision de capturas. Es una vista agrupada del V0, no el diseno completo
de la solucion futura ni un servicio de base de datos ya desplegado.

## 6. Brechas y observaciones para revisar

Estas observaciones son del asistente y quedan pendientes de tratamiento:

- Alcance: OE5 compromete servicios y persistencia central, mientras la seccion
  8.4 los denomina extensiones. Aclarar con el profesor el minimo final exigido;
  no eliminarlos unilateralmente de los objetivos.
- Las casillas marcadas de los criterios de aceptacion de la seccion 10.4
  pueden parecer resultados cumplidos. Separar criterio, implementacion y prueba.
- La tabla bibliografica de pagina 8 mantiene verificaciones pendientes de
  fuentes originales. Completarlas antes de afirmar comparaciones academicas.
- Falta desglosar tareas de diseno con entregables y trazabilidad completa.
- Pablo identifico el prototipo Android `AnotadorVial` en
  `C:\Users\GOMEPAB\AndroidStudioProjects\AnotadorVial`.
  La revision estatica del 11 de septiembre encontro sesiones, anotaciones
  manuales, burbuja flotante, deshacer y guardado/comparticion de CSV.
  No se encontro captura propia de sensores/GPS en el codigo principal revisado.
  No se compilo ni se probo en un dispositivo durante esta revision.
  Es una base para anotaciones; la captura Android de OE2 sigue pendiente.
- Su CSV contiene `trip_id,timestamp,epoch_ms,elapsed_ms,event_type`.
  `src/annotations.py` exige `label` y `seconds_elapsed`, o `timestamp`
  con inicio del viaje. Definir un adaptador, excluir marcadores de inicio/fin
  de las etiquetas y alinear el origen temporal con la captura de sensores.
  No basta con dividir `elapsed_ms` por 1000 si las sesiones inician distinto.
  El timestamp textual Android no incluye zona horaria; revisar el uso de
  `epoch_ms` para evitar interpretar una hora local como UTC.
- `analyze()` calcula calidad pero actualmente no bloquea explicitamente el
  procesamiento cuando el reporte devuelve INVALID. Revisar politica de rechazo.
- El matching de anotaciones permite reutilizar una deteccion para varias
  etiquetas; requiere emparejamiento uno a uno para evaluar TP/FP/FN.
- Revisar sincronizacion de relojes y zonas horarias, tratamiento de gaps y
  muestreo irregular, registro de duplicados y trazabilidad de transformaciones.
- Los reportes guardan parametros, pero falta integrar version del pipeline y
  hash RAW como identificadores de analisis reproducible. Las salidas por viaje
  se sobrescriben al reprocesar; definir historial de ejecuciones.
- No hay evidencia de dataset etiquetado suficiente ni metricas de terreno
  validadas. Desde el 26 de septiembre existe un piloto supervisado exploratorio,
  separado del detector V0; su validacion en terreno sigue pendiente.

## 7. Plan propuesto hasta el 2 de octubre

### Actualizacion de campana: 26 de septiembre

Se recibieron tres ZIP de Sensor Logger y tres CSV de Anotador Vial: Prieto
Norte, Monte Oscuro y Las Mariposas. Hay 39 marcas BACHE, 22 marcas de otros
eventos y 6 marcadores de sesion. Se conservaron los originales en Downloads.
El modulo `src/pilot/` alinea por epoch, genera ventanas y compara umbral con
Random Forest dejando un recorrido fuera. Registra hashes RAW, parametros,
versiones y salidas por ejecucion, sin sustituir los reportes del V0.
Se corrigio en el loader compartido la prioridad del reloj: epoch de muestra,
luego epoch de metadata, finalmente texto. Regenerar exportaciones antiguas
antes de comparar horas absolutas. Hay sectores compartidos entre recorridos;
Pablo confirmo el 26 de septiembre que Monte Oscuro es la ida y Las Mariposas
la vuelta por el mismo corredor. Son sesiones distintas, no corredores
independientes. Mantener ambas juntas en futuras particiones por corredor;
no asumir que los baches de cada sentido son los mismos.
Actualizacion posterior: LOCO ya implementado y ejecutado manteniendo ida/vuelta
juntas. Se revisaron graficamente 39 BACHE y 117 NORMAL sin confirmar causas ni
reetiquetar. Pablo anotaba como acompanante con ambas apps en el mismo telefono;
el mismo soporte estaba mas suelto en Prieto Norte, mas firme en los otros dos.
Ruta y montaje estan confundidos; no presentar las metricas como generalizacion
validada. Evidencia y resultados en docs/REVISION_CAMPANA_2026_09_26.md.
Pablo aclaro despues que marcaba 2-3 s tras el impacto, al estabilizarse el auto.
Se comparo retraso fijo 1.5 vs 2.5 s, sin modificar otros parametros: RF mejora
parcialmente, pero la segmentacion de episodios y deteccion continua no estan
validadas. Se conservaron ambos manifiestos y los RAW. Resultados completos en
docs/PRUEBA_RETRASO_2_5_SEGUNDOS.md; nueva suite: 22 pruebas aprobadas.
no considerar independientes todos los baches ni validar deteccion continua
con metricas de ventanas asistidas por etiquetas. Metodo y comandos en
[la guia de campana](docs/CAMPANA_PILOTO_2026_09_25.md).

### Calendario original

| Fechas | Foco | Entregable previsto |
|---|---|---|
| 11-17 septiembre | Alcance, backlog y diseno | Arquitectura, datos, contrato Android-Python y tareas de diseno verificables. |
| 18-24 septiembre | Implementacion inicial | Meta: captura minima Android, sesion, sensores/GPS, persistencia y exportacion. |
| 25-29 septiembre | Integracion y evidencias | Prueba APK -> ZIP -> V0, trazabilidad y borrador del informe. |
| 30 septiembre-1 octubre | Revision | Informe consistente, evidencia y version de entrega preparada. |
| 2 octubre | Entrega | Informe y avance identificados en Git. |

Este calendario fue propuesto en la conversacion. La APK minima es una meta
por ajustar tras revisar herramientas, disponibilidad y comentarios del profesor.
No implica prometer toda la plataforma en tres semanas.
Priorizar la calidad del diseno (55 %) y una integracion pequena demostrable.

Disenos previstos: contexto y contenedores C4; componentes Android/Python;
secuencias de captura y exportacion; estados de sesion; modelo de datos y
diccionario; contrato ZIP/CSV/JSON con unidades y relojes; protocolo experimental.
Elegir cada diagrama por la pregunta que responde y vincularlo a requisitos.
Archify puede presentar diagramas, pero no certifica conformidad con C4/UML.

## 8. Git y ejecucion

Comprobado el 11 de septiembre: Git existe; ultimo commit local observado
`20f197a` (capturas de pantalla). Antes de crear este documento, `git status`
mostro `?? docs/`. No se comprobo sincronizacion con GitHub.
No se realizaron commits ni push durante el traspaso.
Preservar cambios existentes y revisar que archivos de docs conviene versionar.

Desde la carpeta del proyecto, sin activar el entorno:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
.\.venv\Scripts\python.exe -m pytest -q
```

Para detener un servidor iniciado en terminal: Ctrl+C en esa terminal.
No asumir que hay un servidor activo al abrir el nuevo chat.

## 9. Primer trabajo en el chat nuevo

Implementacion posterior 26/09: AnotadorVial original compilo offline con el JBR
de Android Studio. Se aplico A1a: SessionClock, AnnotationCsvStore y delegacion
desde MainActivity, con 8 tests JVM aprobados y APK debug generada. No hay aun
captura propia, escritor asincrono ni recuperacion de sesion. No se probo en
Mi 10T. Ver docs/etapa2/IMPLEMENTACION_ANDROID_A1.md para respaldo y patch.
Android no tiene Git inicializado; no se hizo commit ni push.

Confirmacion posterior 26/09: mismo proyecto AnotadorVial usado en campaña;
Xiaomi Mi 10T, Android 12, compilacion SKQ1.211006.001 declarados por Pablo.
Solicita integrar la propuesta movil con Etapa 2. Diagnostico de fuente y plan
de incrementos A0-A5 en docs/etapa2/DIAGNOSTICO_ANDROID_Y_ALCANCE.md. No se
modifico ni compilo Android. Captura propia prioritaria; ML movil posterior,
sin eliminar compromisos OE5 ni afirmar todos los incrementos completados.

Actualizacion 26/09: se preparo [docs/etapa2/README.md](docs/etapa2/README.md)
con diseno logico, contratos legacy/V1, flujos, backlog de 26 HU y 18 T,
10 subtareas de diseno propuestas, protocolo PE-0.2 y ficha JSON. Es borrador
para revision: no se declara 100 % de diseno, no hay D cerradas por aprobacion
y las subtareas no sustituyen el backlog original. No se modificaron Android,
pipeline ni RAW. Pendientes: diagramas actualizados, ejemplo V1 validado,
detalle movil/API y acuerdo de alcance, datos de ficha y revision de Pablo.
El codigo del anotador tiene vibracion tras eventos; su efecto en la campaña
no esta medido ni la version desplegada fue verificada. Revisar antes de repetir.

1. Leer este documento y el informe de Etapa 1; comprobar el estado real de Git.
2. Incorporar la respuesta positiva del profesor y el inventario de AnotadorVial
   al backlog. Ambos fueron aportados por Pablo en este chat.
3. Preparar backlog de Etapa 2 vinculado a HU/RF/OE, con tareas de diseno y evidencia.
4. Definir contratos de datos y sincronizacion antes de implementar captura.
5. Revisar entorno Android y acordar un incremento demostrable para la entrega.

Trabajar incrementalmente: diseno, implementacion acotada, pruebas pertinentes
y registro de decisiones. Conservar RAW y separar evidencia real, propuestas
y validaciones pendientes. Pablo solicito un plan de accion para Etapa 2;
se reviso el contexto y luego el codigo del anotador para ajustar ese plan.

Mensaje sugerido para comenzar:

> Continuemos con la Etapa 2 del proyecto. Lee CONTEXTO_ETAPA_2.md y revisa
> el informe de Etapa 1 indicado alli. La entrega es el 2 de octubre de 2026.
> Empecemos por el backlog de diseno y su trazabilidad con la rubrica,
> usando el V0 existente como base.
