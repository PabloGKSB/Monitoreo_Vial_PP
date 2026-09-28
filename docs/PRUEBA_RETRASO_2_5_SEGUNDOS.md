# Prueba de alineacion retrospectiva: 1.5 frente a 2.5 segundos

## Aclaracion del protocolo

Pablo explico que, como acompanante, esperaba aproximadamente 2-3 segundos
desde el impacto, hasta percibir el auto estabilizado, y entonces marcaba BACHE.
La anotacion es una referencia retrospectiva del evento, no su timestamp exacto.
Los picos cercanos podrian pertenecer al mismo episodio; su causa comun y el
retorno a estabilidad no se han verificado independientemente.

Por esta razon, un pico fuera de la ventana anterior no demuestra que la marca
este equivocada. El experimento prueba el punto medio declarado (2.5 s), sin
buscar el retraso que maximice F1. Ya se habia examinado esta campana: sigue
siendo analisis exploratorio, no una nueva validacion independiente.

## Comparacion controlada

Se conservo el manifiesto original. Nueva configuracion:
[campana_2026_09_25_retraso_2_5.json](../configs/campana_2026_09_25_retraso_2_5.json).
Solo cambio el parametro de analisis fixed_delay_seconds de 1.5 a 2.5.
Los metadatos adicionales registran la aclaracion del participante.

- Misma duracion de ventana: 1.5 s. Antes cubria [-2.25,-0.75] s respecto
  del boton; ahora cubre [-3.25,-1.75] s.
- Mismos seis archivos RAW, hashes de codigo fuente, versiones, features,
  semilla, Random Forest de 200 arboles y parametros restantes.
- Mismas 39 marcas BACHE y 117 ventanas NORMAL por modalidad; no se descartaron
  ejemplos para mejorar las cifras. Se comprobo igualdad exacta de los negativos.
- Modalidad peak_assisted intacta, tanto datos como parametros de busqueda;
  no confundir sus resultados con la nueva alineacion fija.
- Ida y vuelta juntas en cada fold LOCO. Se conserva la purga a 50 m y el
  ajuste de umbral/imputacion exclusivamente con entrenamiento.

No se implemento segmentacion variable de episodios ni se confirmo que todo el
evento quepa en 1.5 s. Esta prueba aisla el efecto de desplazar la ventana un
segundo hacia atras. La posicion GPS y velocidad asociadas pueden cambiar con
ese desplazamiento, como corresponde al nuevo instante.

## Resultados

F1 de Random Forest sobre ventanas; mayor es mejor, no equivale a porcentaje
de exactitud ni a deteccion operativa de baches:

| Test | Protocolo | Antes (1.5 s) | Ahora (2.5 s) | Train / test |
|---|---|---:|---:|---:|
| Monte Oscuro + Las Mariposas | LOCO sin purga | 0.652 | 0.717 | 16 / 140 |
| Monte Oscuro + Las Mariposas | LOCO con purga | 0.598 | 0.642 | 12 / 140 |
| Prieto Norte | LOCO sin purga | 0.400 | 0.667 | 140 / 16 |
| Prieto Norte | LOCO con purga | 0.667 | 0.667 | 118 / 16 |

En el fold de ida/vuelta con purga, TP/FP/FN/TN pasan de 32/40/3/65 a
34/37/1/68. La precision sube de 0.444 a 0.479 y el recall de 0.914 a 0.971.
Es una mejora descriptiva, pero 37 negativos candidatos siguen clasificados
como positivos. Esos FP son contra etiquetas provisionales, no inspeccion vial.
En Prieto Norte con purga se mantienen TP=2, FP=0, FN=2, TN=12: solo cuatro
positivos de test. No atribuir significancia estadistica a estos cambios.

El baseline de umbral no mejora uniformemente: su F1 con purga baja de 0.556
a 0.510 en ida/vuelta y sube de 0.444 a 0.600 en Prieto Norte. Por tanto, no
se concluye que cualquier modelo o cualquier recorrido mejore con 2.5 s.

Los picos candidatos fuera de la ventana fija pasan de 19 a 16. Esto no mide
calidad de anotacion ni confirma el instante real; los candidatos siguen siendo
maximos elegidos en un intervalo predefinido. No se sustituyeron etiquetas.

## Interpretacion y decision

**La aclaracion es util y la alineacion de 2.5 s mejora parcialmente el Random
Forest en esta campana. No demuestra aun un detector generalizable.**

Se conservan ambos experimentos y no se sustituye el detector de app.py ni el
manifiesto predeterminado. No se buscaron mas retrasos al conocer estas metricas.
Hay solo dos grupos, muy poco entrenamiento en un sentido, sectores compartidos
y un montaje mas suelto en Prieto Norte. Ademas, las velocidades difieren entre
etiquetas y las ventanas positivas se proponen usando anotaciones.

El siguiente incremento seria definir y probar por separado una delimitacion
de episodios con retorno a un nivel de vibracion local, validarla sobre senales
sinteticas y casos revisados, y congelar ese criterio antes de evaluar nuevas
rutas. No basta unir todos los picos proximos. Las pruebas de deteccion continua
necesitaran propuestas de eventos sin utilizar las marcas de test para ubicarlos.

## Evidencia reproducible

Base: outputs/reports/campana_2026_09_25/20260926T141000184380Z/.
Nueva ejecucion: outputs/reports/retraso_2_5/20260926T142312189350Z/.

- [Informe completo nuevo](../outputs/reports/retraso_2_5/20260926T142312189350Z/INFORME_PILOTO.md).
- [Comparacion antes/despues](../outputs/reports/retraso_2_5/20260926T142312189350Z/comparacion_retrasos.csv).
- [Metricas por corredor](../outputs/reports/retraso_2_5/20260926T142312189350Z/corridor_metrics.csv).

Los archivos bajo outputs no se incluyen automaticamente en Git. La tabla
comparativa une corridor_metrics.csv de ambas ejecuciones por mode, protocol,
test_route y model, selecciona fixed_delay y resta F1 nuevo menos anterior.
Los informes anteriores se conservaron sin sobrescribirlos.

```powershell
.\.venv\Scripts\python.exe -m src.pilot --input-dir "C:\Users\GOMEPAB\Downloads" --manifest configs/campana_2026_09_25_retraso_2_5.json --output-dir outputs/reports/retraso_2_5
.\.venv\Scripts\python.exe run_tests.py
```

Verificacion: 22 pruebas aprobadas. El test nuevo comprueba que cambiar el
retraso mueve las positivas fijas, sin cambiar las anotaciones temporales, los
negativos o la modalidad asistida por picos en la fixture sintetica. Tambien se
comprobaron los identificadores e igualdad de negativos y modalidad por picos
en las ejecuciones reales, asi como coincidencia de entradas, codigo y versiones.
