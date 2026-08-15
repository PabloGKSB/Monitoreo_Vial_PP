# Monitoreo vial - Prototipo V0

Aplicacion experimental para detectar y georreferenciar posibles irregularidades viales mediante los sensores de un smartphone. Recibe un ZIP de recorrido, conserva los datos originales, evalua su calidad, procesa el acelerometro y muestra anomalias y patrones espaciales en un mapa.

La explicación detallada de cada módulo, las fórmulas matemáticas, decisiones académicas y hoja de ruta futura se encuentra en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md).

> **Estado actual:** detector V0 basado en procesamiento de senales y estadistica robusta. No es un clasificador de Machine Learning ni una evaluacion vial cientificamente validada. `LEVE`, `MEDIA`, `ALTA` y `BUENO`, `REGULAR`, `MALO` son categorias experimentales para explorar patrones.

## Instalacion en Windows y Visual Studio Code

Se requiere Python 3.11 o superior. En la terminal de VS Code:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En equipos donde `python` apunta a MSYS2, puede crearse un entorno estandar con `uv venv .venv --python 3.12` y luego instalar con `uv pip install --python .venv\Scripts\python.exe -r requirements.txt`.

## Ejecucion

```powershell
streamlit run app.py
```

La interfaz permite elegir un ZIP existente, subir otro, cambiar el umbral experimental y la longitud de segmento, revisar la calidad de sensores, filtrar eventos y observar 5 segundos antes y despues de cada deteccion.

## Datos y resultados

Coloque los recorridos originales en `data/raw/*.zip`. Durante la transicion, la interfaz tambien descubre los ZIP existentes en `Data/`. El loader lee los CSV directamente desde el ZIP y nunca extrae, modifica ni sobrescribe datos RAW.

El requisito minimo es acelerometro + GPS. Giroscopio, orientacion, brujula, metadata y variantes no calibradas son opcionales. Los nombres de archivo y columnas se normalizan antes de validarlos.

Cada analisis genera:

- `outputs/events/eventos_detectados.csv`: ultimo resultado con el esquema canonico solicitado.
- `outputs/events/<trip_id>_eventos.csv`: copia identificada por recorrido.
- `outputs/reports/<trip_id>_segmentos.csv`: agregacion espacial experimental.
- `outputs/reports/<trip_id>_analisis.json`: calidad, resumen, preprocesamiento y parametros exactos.
- `outputs/maps/<trip_id>.html`: mapa autocontenido basado en OpenStreetMap/CartoDB, sin API comercial.

## Arquitectura

`app.py` contiene solo presentacion. `src/analyzer.py` expone `TripAnalyzer`, fachada reutilizable por Streamlit y por una futura API.

```text
Streamlit
    -> TripAnalyzer
        -> loader + quality
        -> preprocessing + features + detector
        -> gps + segmentation + scoring
        -> CSV / JSON / mapa
```

- `src/config.py`: parametros centralizados e incluidos en cada reporte.
- `src/loader.py`: inspeccion tolerante y lectura segura del ZIP.
- `src/quality.py`: duracion, frecuencia real, cortes y calidad GPS.
- `src/preprocessing.py`: magnitud, compensacion de gravedad, suavizado y jerk.
- `src/features.py`: caracteristicas por ventanas temporales solapadas.
- `src/detector.py`: score robusto adaptado al ruido del recorrido y agrupacion temporal.
- `src/gps.py`: distancia, velocidad en km/h y asociacion temporal con tolerancia.
- `src/segmentation.py` y `src/scoring.py`: indicadores espaciales experimentales.
- `src/annotations.py`: carga y comparacion de etiquetas manuales.
- `src/maps.py`: representacion Folium independiente del procesamiento.

## Decisiones de procesamiento

### Gravedad y orientacion

La magnitud `sqrt(x^2 + y^2 + z^2)` reduce la dependencia de la orientacion fisica. Si la magnitud mediana esta entre 6 y 13 m/s2, el sistema interpreta que la gravedad esta incluida, estima su vector con un filtro pasa-bajos de 0.35 Hz y lo resta. Si la magnitud es baja, considera que la aplicacion ya entrega aceleracion lineal. La decision y la frecuencia real quedan registradas en el JSON.

### Ventanas y caracteristicas

Las ventanas predeterminadas duran 0.5 s y tienen 50 % de solapamiento. Calculan media, desviacion, varianza, min/max, pico a pico, RMS, magnitud maxima/media/desviacion, jerk maximo/RMS, energia, percentiles y factor de cresta. Las definiciones breves estan en `FEATURE_DESCRIPTIONS` dentro de `src/features.py`.

### Detector

El score combina magnitud maxima, RMS, desviacion, jerk y energia. Cada variable se transforma con `log1p`, se normaliza respecto de la mediana y MAD del propio viaje y solo aporta su desviacion positiva. Esto adapta el detector al ruido habitual sin depender de un unico umbral absoluto. Las ventanas anormales separadas por menos de 1 s se agrupan como un evento.

El umbral, los pesos y las bandas de severidad son parametros V0 sujetos a calibracion con anotaciones reales. No deben interpretarse como limites normativos.

### Segmentos

El recorrido se divide cada 20 m. Por segmento se agregan eventos, scores, RMS, energia, velocidad y observaciones. `road_condition_score` combina rangos relativos de carga de eventos y vibracion dentro del mismo viaje. Sirve para visualizar zonas contrastantes; no permite todavia comparar cientificamente pavimentos, vehiculos o telefonos diferentes.

## Anotaciones manuales

Los CSV se guardan en `data/annotations/` y pueden usar una de estas formas:

```csv
timestamp,label
2026-08-14 09:19:30,BACHE
```

```csv
seconds_elapsed,label
120.5,LOMO
```

`src/annotations.py` busca el evento detectado mas cercano dentro de una tolerancia configurable (5 s por defecto), sin inventar coincidencias fuera de ella.

## Pruebas

```powershell
pytest -q
```

Las pruebas generan ZIP, senales, impactos, cortes, timestamps y GPS sinteticos; no necesitan los recorridos reales. Para reproducibilidad, los parametros efectivos se exportan en cada reporte.
