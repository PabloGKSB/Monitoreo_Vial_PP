# Primera campana piloto: 25 de septiembre de 2026

## Proposito y estado

Pipeline separado del detector V0 de Streamlit para estudiar **BACHE vs NORMAL**.
Se implemento a partir de las tres parejas Sensor Logger / Anotador Vial
proporcionadas por Pablo. No cambia automaticamente el modelo usado por app.py.
La comparacion usa ventanas asistidas por anotaciones, no deteccion continua.

## Entradas y correspondencias explicitas

La configuracion versionable esta en
[configs/campana_2026_09_25.json](../configs/campana_2026_09_25.json).

| ZIP Sensor Logger | CSV Anotador Vial | BACHE | Otras marcas |
|---|---|---:|---:|
| Prieto_Norte-2026-09-25_21-38-04.zip | monte_Verde_20260925_183838_234_anotaciones.csv | 4 | 3 |
| Monte_Oscuro-2026-09-25_21-48-30.zip | monte_Verde_2_20260925_184827_097_anotaciones.csv | 22 | 10 |
| Las_Mariposas-2026-09-25_22-01-43.zip | monte_Verde_3_20260925_190153_148_anotaciones.csv | 13 | 9 |

Los nombres monte_Verde NO identifican rutas. La asociacion anterior proviene
del usuario. Inicio/fin son limites de monitoreo, no clases de eventos.
Las otras marcas son CAMINO_MALO, LOMO_DE_TORO, GIRO y OTRO.
Las 39 marcas BACHE no equivalen a 39 defectos fisicos independientes.
Los archivos se leen directamente en la carpeta indicada, sin mover ni modificar RAW.

### Aclaracion del participante: ida y vuelta

Pablo confirmo el 26 de septiembre de 2026 que Monte Oscuro es el recorrido
de ida y Las Mariposas el de vuelta por el mismo corredor. La similitud GPS
es esperada y no implica que los archivos esten duplicados. Son sesiones
distintas, pero no rutas geograficamente independientes. El sentido y el
carril pueden cambiar los defectos atravesados; no se debe asumir que cada
marca BACHE tiene una correspondencia en el otro recorrido.

Para una futura evaluacion de generalizacion a corredores nuevos, agrupar
ambas sesiones bajo el mismo corredor y mantenerlas juntas en train o test.
Los resultados actuales separados por route_id se conservan como exploratorios;
no se recalcularon al incorporar inicialmente esta aclaracion. Posteriormente
se anadio y ejecuto LOCO: ver [revision ampliada](REVISION_CAMPANA_2026_09_26.md).
La comparacion ida/vuelta
puede analizarse por separado, sin presentarla como prueba en una ruta nueva.

## Correccion del reloj del V0

Se detecto que el loader anterior reemplazaba epochs por la hora textual de
metadata interpretada como local. En estos archivos el texto muestra 21:48,
pero el epoch corresponde a 21:48 UTC / 18:48 America/Santiago.
La conversion anterior habria desplazado tres horas la sincronizacion.

Desde esta revision, el epoch de cada muestra tiene prioridad. Para sensores
sin epoch, se usa recording epoch time + seconds_elapsed; el texto con zona
es un ultimo recurso. El campo time original se conserva. Se admite epoch
en segundos, milisegundos, microsegundos o nanosegundos segun su magnitud.
Esta inferencia esta pensada para fechas contemporaneas, no relojes arbitrarios.

El piloto exige epoch de acelerometro. Las anotaciones se alinean mediante
epoch_ms respecto del origen de Sensor Logger. Nunca se utiliza elapsed_ms
del Anotador como si ambas sesiones hubiesen comenzado simultaneamente.
El registro generado usa UTC; la hora local solo se utiliza para presentacion.
Los CSV antiguos ya exportados conservan su version anterior: deben regenerarse
antes de comparar sus horas absolutas con esta campana.

## Metodo reproducible

1. Leer parejas del manifiesto y calcular SHA-256 de cada entrada.
2. Auditar epoch RAW: ausencias, duplicados y retrocesos. Medir intervalos,
   frecuencia mediana y frecuencia efectiva tras normalizacion.
3. Restringir muestras al intervalo comun de sensores y monitoreo manual.
4. Proponer picos en [-3,+1] s alrededor de cada anotacion y conservar el
   retraso observado como candidato sin revision, nunca como verdad de terreno.
5. Construir dos datasets independientes de ventanas de 1.5 s:
   fixed_delay, centrado 1.5 s antes del boton; peak_assisted, centrado en el pico.
6. Excluir ventanas positivas incompletas, con gaps >100 ms, cobertura <80 %,
   valores no finitos o solapamiento con otra positiva aceptada. Exportar motivos.
7. Seleccionar NORMAL candidato desde una grilla no solapada, con semilla 42,
   cuyo intervalo completo este fuera de +/-8 s de TODAS las marcas de eventos.
   Objetivo 3 negativos por positivo; no elegirlos segun amplitud de senal.
8. Extraer estadisticas de X/Y/Z/magnitud de acelerometro, aceleracion total
   y giroscopio, conservando velocidad y GPS cercano (tolerancia 2 s).
9. Comparar umbral de pico de aceleracion y Random Forest en LeaveOneGroupOut
   con route_id como grupo, sin mezclar modalidades.
10. Repetir con purga de entrenamiento a menos de 50 m de cualquier fijacion
    GPS del recorrido de test; descartar ubicaciones de train desconocidas.

El margen para NORMAL no garantiza ausencia de defectos: CAMINO_MALO puede
representar un tramo mucho mayor. Es obligatorio revisar las etiquetas antes
de utilizar este piloto como dataset final. Las ventanas que no son BACHE no
se convierten automaticamente en NORMAL.

## Features y unidades

Por canal se calculan media, minimo, maximo, maximo absoluto, rango, desviacion
poblacional, RMS, P95 con signo, media de cuadrados y tres estadisticas de
derivada: maximo absoluto, RMS y P95 absoluto.

Son 144 features inerciales y velocidad en km/h. Las coordenadas, nombres,
timestamps, retraso del anotador, etiqueta e identificadores NO son predictores.
La derivada de aceleracion se expresa en m/s3; la del giroscopio en rad/s2
(aceleracion angular, aunque el sufijo comun de columna sea jerk).
energy es media de cuadrados y equivale a RMS al cuadrado; no son joules.
Las variables redundantes/correlacionadas se mantienen como baseline inicial.

Se emplean muestras nativas sin remuestreo ni filtrado del V0: los resultados
no son directamente comparables con features de magnitud suavizada del V0.
Los gaps se rechazan antes de derivar. TotalAcceleration conserva gravedad.
Gravity y Orientation se cargan, pero no se realiza una rotacion a vertical:
primero se necesita validar convenciones de ejes/cuaterniones y montaje.

## Entrenamiento y limites de las metricas

El umbral maximiza F1 exclusivamente en entrenamiento; en empate se elige el
mayor umbral. Random Forest usa 200 arboles, min_samples_leaf=2, pesos balanced,
semilla 42 y umbral de decision 0.5. La imputacion mediana de velocidad faltante
se ajusta dentro del entrenamiento. No se seleccionan features mirando el test.
Las importancias por impureza no son efectos causales ni justifican seleccionar
variables usando todos los recorridos antes de dividir.

Se exportan Precision, Recall, F1 y TN/FP/FN/TP por fold/modelo/modalidad.
Los folds sin ambas clases se marcan INSUFFICIENT_CLASSES, sin metricas inventadas.
La proporcion 1:3 es de muestreo; no representa la prevalencia real en la via.
No extrapolar precision a produccion ni calcular FP/km con estas ventanas.

Ambas modalidades dependen de marcas para proponer positivos; peak_assisted
ademas busca el maximo con informacion de la etiqueta. Ninguna acredita un
detector capaz de encontrar baches en un recorrido sin anotaciones.
La purga espacial es un diagnostico conservador basado en centros de ventana
y fijaciones GPS; no prueba independencia por defecto fisico. Revisar sectores
compartidos y recolectar rutas nuevas antes de validar generalizacion.

Fundamento de la evaluacion por grupos y ajuste solo en train:
[Scikit-learn: validacion cruzada](https://scikit-learn.org/stable/modules/cross_validation.html)
y [prevencion de fuga de informacion](https://scikit-learn.org/stable/common_pitfalls.html).
Los tiempos, radios y parametros de este piloto son decisiones experimentales,
no recomendaciones normativas de esas fuentes.

## Ejecucion

Dependencias opcionales para este experimento:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-pilot.txt
.\.venv\Scripts\python.exe -m src.pilot --input-dir "C:\Users\GOMEPAB\Downloads"
.\.venv\Scripts\python.exe -m pytest -q
```

Si el entorno fue creado con uv y no contiene pip:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-pilot.txt
```

Parametros alternativos: editar una copia del manifiesto y pasar --manifest.
Las salidas van a outputs/reports/campana_2026_09_25/<ejecucion_UTC>/;
cada ejecucion conserva sus resultados y no sobrescribe las anteriores.
La separacion por carpetas no sustituye el versionado Git.

## Archivos del nuevo modulo

- src/pilot/data.py: configuracion, lector epoch Anotador, auditoria y features.
- src/pilot/dataset.py: candidatos, ventanas, exclusiones y negativos reproducibles.
- src/pilot/evaluation.py: umbral, bosque, folds y purga espacial.
- src/pilot/reporting.py: informe y graficos locales de revision por anotacion.
- src/pilot/__main__.py: comando que coordina y registra procedencia.
- tests/test_pilot.py: relojes, gaps, exclusiones, repetibilidad y folds.

Las salidas incluyen dataset.csv, candidates.csv, annotations.csv, audit.json,
metrics.csv, predictions.csv, errors.csv, feature_importances.csv,
route_overlap.csv y provenance.json. La tabla de solapamiento mide proporcion
de fijaciones cercanas, no proporcion exacta de longitud compartida.
INFORME_PILOTO.md resume lo calculado. Los revision_*.html son autocontenidos;
abrirlos en el navegador y elegir una anotacion para ver sus senales.

## Siguiente evidencia academica

### Resultado ejecutado el 26 de septiembre

Informe local de esta ejecucion:
[INFORME_PILOTO.md](../outputs/reports/campana_2026_09_25/20260926T132106441002Z/INFORME_PILOTO.md).
Estos artefactos estan bajo outputs y no se incluyen automaticamente en Git.

Se aceptaron 39 ventanas BACHE y 117 NORMAL candidatas por modalidad.
Las modalidades reutilizan los mismos eventos: no son 312 ejemplos independientes.
En los cuatro sensores auditados por recorrido no se encontraron epochs RAW
ausentes, duplicados ni regresivos. El GPS de Prieto Norte presenta un intervalo
maximo de aproximadamente 3.29 s; no confundir frecuencia nominal con continuidad.

El 100 % de las fijaciones de Monte Oscuro tiene alguna fijacion de Las Mariposas
a <=50 m, y viceversa. Esto indica cobertura espacial muy similar, no prueba que
se hayan anotado los mismos defectos. Al purgar cercania espacial, los folds con
esas rutas como test conservan solo 12 ventanas de entrenamiento. Las metricas
son muy fragiles: ni la division por nombre de archivo ni el mejor F1 constituyen
evidencia suficiente de generalizacion. Prieto Norte aporta solo cuatro positivos.

La suite completa termino con 19 pruebas aprobadas. Se verificaron nuevamente
los SHA-256 de las seis entradas contra provenance.json tras la ejecucion.

### Pendientes de revision

Confirmar quien anotaba, si ambas apps funcionaban en el mismo telefono,
vehiculo y montaje utilizado. Revisar los 39 candidatos y los negativos,
registrar inicio/fin de tramos CAMINO_MALO y asignar identificadores a defectos
repetidos. Luego evaluar deteccion continua, matching uno a uno e incertidumbre
temporal, con una campana reservada que no se use para ajustar parametros.

Actualizacion: Pablo confirmo ambas apps en el mismo telefono, anotacion por el
acompanante y mismo soporte, mas suelto en Prieto Norte y mas ajustado en ida/vuelta.
La revision de senales y la evaluacion agrupada ya ejecutadas se detallan en
[REVISION_CAMPANA_2026_09_26.md](REVISION_CAMPANA_2026_09_26.md).
