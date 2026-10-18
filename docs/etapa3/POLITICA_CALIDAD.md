# Politica compartida de procesamiento

Fecha: 2026-10-10. Version: **quality-policy-1**. Evidencia EV-13.
E3-03/T-10 cerradas para el criterio tecnico del backlog; no es validacion del
detector, de umbrales cientificos o de continuidad de la APK.

## Estados y reglas

| Caso | V0 | API de inspeccion |
|---|---|---|
| Datos requeridos INVALID | BLOCKED_INVALID, event_count null; no preprocesar, detectar ni clasificar segmentos. | Inspeccion disponible, detection NOT_EVALUATED; politica niega deteccion e incluye INVALID_REQUIRED_DATA. |
| capture-preview-2 | NOT_EVALUATED, event_count null; mapa/calidad/marcas disponibles. | Igual, con motivo NATIVE_DETECTOR_NOT_VALIDATED e INSPECTION_ONLY. |
| Legado elegible, al menos 10 ventanas | EVALUATED; event_count puede ser cero si realmente se ejecuto el detector experimental. | Sigue siendo INSPECTION_ONLY: no ejecuta el detector. |
| Legado sin suficientes ventanas elegibles | NOT_EVALUATED, event_count null; no clasificar pavimento. | Inspeccion sin detecciones. |

INVALID se determina sobre los sensores requeridos: aceleracion y GPS. Un sensor
opcional invalido mantiene WARNING si los requeridos son utilizables. La prueba
detecta relojes no crecientes, menos de dos tiempos finitos, y aceleracion con
menos de dos registros utilizables o al menos la mitad no finitos. En GPS,
al menos la mitad de coordenadas ausentes/fuera de rango produce INVALID. Estas
reglas son operativas y conservadoras, no limites normativos ni calibracion.

## Continuidad

- Aceleracion: partir antes de filtrar ante intervalos superiores a
  max(minimum_gap_seconds, gap_factor por mediana del intervalo), valores por
  defecto 1 s y factor 8. Una fila no finita tambien rompe el bloque.
- Gravedad, suavizado y jerk se calculan dentro de cada bloque; jerk inicia en
  cero. No se interpolan muestras perdidas ni se mezclan filtros entre bloques.
- Una ventana debe estar completa dentro de un bloque. La configuracion actual
  usa 0,5 s, 50 % de solapamiento y al menos cinco muestras.
- Una ventana candidata solo es elegible si cabe enteramente dentro del tiempo
  observado de un tramo GPS. prepare_gps separa tramos ante intervalos >2 s.
  Se excluyen bordes sin cobertura y ventanas que atraviesen huecos GPS.
- Eventos no se agrupan entre bloques de senal o tramos GPS diferentes, aunque
  su separacion sea inferior al tiempo de merge configurado.
- Segmentos GPS separados no se conectan como una sola geometria de estado vial.
  Un segmento sin ventanas tiene SIN_DATOS y score ausente, no BUENO; tampoco
  participa en los rangos relativos de vibracion.

El reporte temporal de cada sensor usa su propio umbral de gaps; no equivale a
la cobertura exigida para ventanas GPS. No se deduce calidad cientifica de un
promedio de frecuencia. La inspeccion del ZIP propio conserva los descartes y
los intervalos originales: esta mejora no recupera muestras ni cambia la APK.

## Evidencia

Implementacion: processing_policy.py, analyzer.py, preprocessing.py, features.py,
detector.py, gps.py, segmentation.py, scoring.py, quality.py y estados de app.py.
La API usa la misma politica y anade INSPECTION_ONLY.

tests/test_processing_policy.py comprueba bloqueo antes de procesar/scoring,
aislamiento de filtros, ventanas y merge, registros no finitos, exclusiones GPS,
insuficiencia de datos y segmentos SIN_DATOS. tests/test_app_quality.py comprueba
con AppTest el aviso de bloqueo y la metrica No evaluadas en V0; no verifica
descarga de teselas externas en navegador.

ZIP real del 28/09: calidad WARNING, 1.127 fijaciones, dos tramos, distancia
observada 7,494463 km y 2.315 descartes declarados. El V0 ahora exporta
event_count null y NOT_EVALUATED. Recibo local:
`outputs/reports/quality_policy_20261010.json`, excluido de Git.

Suite del incremento completo: **87 passed, 1 skipped, 1 warning in 6.72s**.
La prueba omitida requiere PostgreSQL/PostGIS real, no es de calidad.

Los informes y modelos historicos no se reentrenaron ni recalcularon. La seleccion
de ventanas y el preprocesamiento han cambiado; comparar nuevas ejecuciones con
el piloto anterior requiere registrar la version y regenerar sus resultados.
El contrato congelado de features para un detector nativo sigue pendiente.
