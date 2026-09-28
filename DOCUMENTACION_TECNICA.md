# Guía técnica y académica del Prototipo V0

## 1. Propósito de este documento

Este documento explica cómo está construido el prototipo de monitoreo vial, qué responsabilidad tiene cada archivo Python, por qué se eligieron sus librerías, qué fundamentos matemáticos utiliza y cómo podría evolucionar hacia un sistema académico y tecnológico más completo.

El sistema actual **no diagnostica baches de forma validada**. Detecta ventanas de señal que se apartan del comportamiento habitual del mismo recorrido y las presenta como **posibles irregularidades viales**.

Esta diferencia es esencial:

- Una **anomalía** es un comportamiento estadísticamente inusual.
- Un **bache, lomo, junta o pavimento deteriorado** es una clase física que requiere evidencia y etiquetas de terreno.
- El V0 resuelve la primera tarea y prepara los datos para estudiar posteriormente la segunda.

## 2. Visión general del flujo

```text
ZIP del smartphone
        |
        v
Loader y normalización
        |
        v
Control de calidad --------> Informe de advertencias
        |
        v
Preprocesamiento del acelerómetro
        |
        v
Ventanas y características
        |
        v
Score robusto de anomalía
        |
        v
Agrupación temporal de eventos
        |
        v
Asociación con GPS
        |
        +------------> eventos_detectados.csv
        |
        v
Segmentación espacial de la ruta
        |
        +------------> segmentos.csv
        |
        v
Mapa y dashboard Streamlit
```

La lógica de análisis está separada de la interfaz. `app.py` no calcula eventos directamente: solicita el trabajo a `TripAnalyzer`. Gracias a esto, en el futuro se podrá reemplazar Streamlit por FastAPI, una aplicación Android o un proceso por lotes sin reescribir el detector.

## 3. Estructuras de datos principales

### `TripData`

Representa un recorrido cargado desde un ZIP. Contiene:

- identificador del recorrido;
- ruta del ZIP original;
- un `DataFrame` por sensor;
- relación entre sensor y nombre de archivo original;
- advertencias encontradas durante la carga.

Los datos RAW no se sobrescriben. Las columnas derivadas se crean sobre copias en memoria.

### `QualityReport`

Agrupa el estado general del recorrido y el detalle de cada sensor: frecuencia estimada, cantidad de registros, duración, cortes, problemas y métricas GPS.

### `AnalysisResult`

Es el resultado completo que circula entre el núcleo y la interfaz. Contiene datos cargados, calidad, aceleración procesada, ventanas, eventos, GPS, segmentos, resumen y configuración exacta.

### `AnalysisConfig`

Concentra todos los parámetros experimentales. Al ser una `dataclass` inmutable, reduce cambios accidentales y permite guardar los parámetros usados en cada ejecución.

## 4. Explicación de `app.py`

`app.py` es la capa de presentación construida con Streamlit.

### Responsabilidades

- Descubrir ZIP en `data/raw/` y en la carpeta heredada `Data/`.
- Aceptar un ZIP subido manualmente.
- Permitir modificar el umbral del detector y la longitud de los segmentos.
- Ejecutar `TripAnalyzer` con caché para no repetir un análisis costoso en cada interacción.
- Mostrar resumen, calidad, cortes, mapa, eventos y señales alrededor de un evento.
- Exportar los resultados y ofrecer descargas.

### Funciones

- `_analyze`: ejecuta y almacena en caché un análisis según archivo, fecha de modificación y configuración.
- `_uploaded_path`: guarda una copia de trabajo en `data/processed/uploads/`. Usa SHA-256 para evitar duplicados y nunca reemplaza el RAW.
- `_duration_text`: convierte segundos a una representación legible.
- `_quality_table`: transforma el reporte de calidad en una tabla para la interfaz.
- `_signal_figure`: muestra magnitud dinámica y señal suavizada durante ±5 segundos.
- `_gyro_figure`: muestra magnitud angular si hay giroscopio disponible.
- `main`: construye y coordina toda la interfaz.

El dashboard no es parte del algoritmo científico. Es una herramienta para inspeccionar resultados, encontrar errores y comunicar el comportamiento del prototipo.

## 5. Explicación de los módulos de `src/`

### `src/__init__.py`

Define la interfaz básica del paquete y permite importar directamente `AnalysisConfig`, `TripData` y `load_trip`.

### `src/config.py`

Centraliza parámetros como:

| Parámetro | Valor V0 | Función |
|---|---:|---|
| `window_seconds` | 0.5 s | Duración de cada ventana |
| `window_overlap` | 0.5 | Solapamiento del 50 % |
| `event_merge_seconds` | 1.0 s | Distancia máxima para unir detecciones |
| `gps_max_time_difference` | 2.0 s | Tolerancia de asociación GPS |
| `road_segment_meters` | 20 m | Longitud de segmento vial |
| `annotation_tolerance_seconds` | 5 s | Tolerancia contra etiquetas manuales |
| `gravity_cutoff_hz` | 0.35 Hz | Corte para estimar gravedad |
| `smoothing_cutoff_hz` | 12 Hz | Corte del suavizado dinámico |
| `detector_threshold` | 3.5 | Umbral experimental del score |

Los valores son hipótesis de trabajo. Deben calibrarse mediante recorridos anotados, sensibilidad y análisis de errores.

### `src/utils.py`

Contiene utilidades pequeñas y reutilizables:

- `normalize_name`: elimina acentos, espacios y símbolos para comparar nombres de forma tolerante.
- `elapsed_to_timestamp`: interpreta timestamps de época y crea una línea de tiempo alternativa usando segundos transcurridos.

### `src/loader.py`

Lee los CSV directamente desde el ZIP mediante `zipfile`, sin extraerlos al directorio RAW.

Su estrategia es:

1. Inspeccionar todos los archivos del ZIP.
2. Considerar únicamente CSV reconocibles.
3. Asociar variantes de nombres con sensores canónicos.
4. Normalizar columnas.
5. Convertir variables numéricas con manejo de valores inválidos.
6. Ordenar y eliminar timestamps duplicados.
7. Validar columnas mínimas.
8. Exigir acelerómetro + GPS y tratar los demás sensores como opcionales.
9. Conservar el epoch absoluto de cada muestra. Si falta, reconstruirlo con `recording epoch time` de metadata y el tiempo transcurrido; usar hora textual y zona solo como ultimo recurso. Internamente los timestamps son UTC.

El campo `time` original se conserva. La columna derivada `timestamp` se ancla a `recording time` y `recording timezone`, mientras `seconds_elapsed` se usa para cálculos de diferencias temporales.

### `src/quality.py`

Evalúa si un sensor puede analizarse y si presenta problemas temporales.

La frecuencia típica se estima como:

```math
f_s = \frac{1}{\mathrm{mediana}(\Delta t_i)}
```

Se usa la mediana y no la media porque un corte grande alteraría fuertemente el promedio.
Un intervalo se considera corte cuando:

$$
\Delta t_i > \max(T_{\mathrm{min}},\; k\,\mathrm{mediana}(\Delta t))
$$

En el V0, $T_{\mathrm{min}}=1$ segundo y $k=8$. Esto es una regla adaptativa, pero sus valores todavía deben validarse.
Para GPS se revisan coordenadas ausentes o fuera de rango, precisión horizontal, velocidades negativas y cantidad de observaciones.

Estados:

- `OK`: no se detectaron problemas según las reglas V0.
- `WARNING`: el recorrido puede usarse, pero existe una condición que debe informarse.
- `INVALID`: falta información mínima o la serie no permite análisis.

### `src/preprocessing.py`

Transforma el acelerómetro en señales más útiles para detectar impactos.

#### Magnitud

Para reducir la dependencia de la orientación física del teléfono:

$$
a_m(t)=\sqrt{a_x(t)^2+a_y(t)^2+a_z(t)^2}
$$

La magnitud es invariante ante rotaciones ideales del sistema de ejes. Sin embargo, pierde información direccional: no distingue por sí sola una aceleración vertical de una lateral.

#### Compensación de gravedad

Si la mediana de la magnitud está entre 6 y 13 m/s², el sistema asume que la señal probablemente incluye gravedad. Estima un vector lento con un filtro pasa-bajos:

$$
\hat{\mathbf{g}}(t)=LPF\{\mathbf{a}(t)\}
$$

y calcula:

$$
\mathbf{a}_{din}(t)=\mathbf{a}(t)-\hat{\mathbf{g}}(t)
$$

En los ZIP reales, `Accelerometer.csv` posee magnitudes medianas bajas y se interpreta como aceleración lineal ya compensada. `TotalAcceleration.csv` conserva aproximadamente $g$.

Se utiliza un filtro Butterworth de segundo orden en secciones de segundo orden (`SOS`). `sosfiltfilt` filtra hacia adelante y hacia atrás, evitando el desfase temporal que movería artificialmente el instante de un impacto. Esta operación es apropiada para análisis offline; una aplicación en tiempo real necesitará un filtro causal.

#### Jerk

El jerk aproxima la rapidez con la que cambia la aceleración:

$$
j_i=\frac{a_i-a_{i-1}}{t_i-t_{i-1}}
$$

Un impacto breve puede generar jerk alto incluso cuando la amplitud no es extrema. También amplifica ruido, por lo que se calcula después del suavizado.

### `src/features.py`

Divide la señal en ventanas de 0.5 segundos con 50 % de solapamiento. Con ese ajuste comienza una ventana nueva cada 0.25 segundos.

Para una ventana con $N$ muestras $x_i$:

#### Media

$$
\bar{x}=\frac{1}{N}\sum_{i=1}^{N}x_i
$$

#### Varianza y desviación estándar

$$
\sigma^2=\frac{1}{N}\sum_{i=1}^{N}(x_i-\bar{x})^2
$$

$$
\sigma=\sqrt{\sigma^2}
$$

Miden dispersión o variabilidad vibracional.

#### RMS

$$
x_{RMS}=\sqrt{\frac{1}{N}\sum_{i=1}^{N}x_i^2}
$$

RMS representa amplitud efectiva y es común en análisis de vibraciones.

#### Energía V0

$$
E=\frac{1}{N}\sum_{i=1}^{N}x_i^2=x_{RMS}^2
$$

Aquí se denomina energía por conveniencia de características, pero matemáticamente es potencia media discreta, no energía física total en joules.

#### Pico a pico

$$
x_{pp}=\max(x)-\min(x)
$$

#### Factor de cresta

$$
CF=\frac{\max(|x|)}{x_{RMS}}
$$

Un factor alto sugiere un comportamiento impulsivo respecto de la vibración habitual.

También se calculan mínimo, máximo, percentiles, magnitud máxima/media/desviación y jerk máximo/RMS. `FEATURE_DESCRIPTIONS` mantiene una descripción corta de cada característica.

### `src/detector.py`

Implementa el detector adaptativo sin Machine Learning supervisado.

Las variables del score son:

1. magnitud máxima;
2. RMS;
3. desviación estándar;
4. jerk máximo;
5. energía.

Primero se comprime cada variable positiva:

$$
u=\log(1+x)
$$

Esto evita que un único valor extremo domine todo el score.

Después se calculan mediana y desviación absoluta mediana:

$$
MAD = \mathrm{mediana}\left(\left|u_i - \mathrm{mediana}(u)\right|\right)
$$

La escala robusta es:

$$
s=1.4826\,MAD
$$

El factor 1.4826 hace que MAD sea comparable con la desviación estándar cuando los datos siguen aproximadamente una distribución normal. Si MAD es cero se usa el rango intercuartílico:

$$
s\approx\frac{Q_{75}-Q_{25}}{1.349}
$$

El z-score positivo queda:

$$
z_k^+ = \max\left(0,\frac{u_k-\mathrm{mediana}(u_k)}{s_k}\right)
$$

El score combinado es:

$$
S=0.25z_{pico}^{+}+0.20z_{RMS}^{+}+0.20z_{std}^{+}+0.20z_{jerk}^{+}+0.15z_{energía}^{+}
$$

Una ventana es anómala cuando $S\geq3.5$ con la configuración predeterminada.

Bandas experimentales:

- `LEVE`: $3.5 \leq S < 5.25$.
- `MEDIA`: $5.25 \leq S < 8.75$.
- `ALTA`: $S \geq 8.75$.

Estas bandas derivan del umbral configurado, no de una norma vial. Ventanas anómalas próximas se unen para evitar contar varias veces un mismo impacto físico.

### `src/gps.py`

Limpia coordenadas, convierte velocidad de m/s a km/h y calcula distancia acumulada.

La distancia Haversine entre dos coordenadas se obtiene mediante:

$$
a=\sin^2\left(\frac{\Delta\varphi}{2}\right)+\cos(\varphi_1)\cos(\varphi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)
$$

$$
d=2R\arcsin(\sqrt{a})
$$

donde $R=6\,371\,008.8$ m, $\varphi$ es latitud y $\lambda$ longitud en radianes.

Para cada evento se busca el GPS temporalmente más cercano. Solo se asigna si:

$$
|t_{evento}-t_{GPS}|\leq2\text{ s}
$$

Si no cumple, se guarda `GPS_NOT_AVAILABLE`. No se interpolan ni inventan coordenadas.

### `src/scoring.py`

Construye un índice experimental por segmento. Primero define carga de eventos:

$$
B=n_{eventos}\cdot S_{máximo}
$$

Luego obtiene rangos percentiles internos $R_B$ y $R_V$ para carga de eventos y RMS. Si hay eventos:

$$
RCS=100(0.7R_B+0.3R_V)
$$

Si no hay eventos:

$$
RCS=30R_V
$$

Clasificación V0:

- `BUENO`: $RCS<40$.
- `REGULAR`: $40\leq RCS<70$.
- `MALO`: $RCS\geq70$.

Este índice es **relativo al propio recorrido**. No debe compararse directamente entre teléfonos, vehículos o días hasta realizar normalización y validación externa.

### `src/segmentation.py`

Divide la distancia acumulada en intervalos de 20 m. Asocia ventanas y eventos al GPS más cercano y agrega:

- cantidad de eventos;
- score medio y máximo;
- RMS medio;
- intensidad vibracional;
- velocidad media;
- cantidad de observaciones;
- coordenadas iniciales y finales.

Luego solicita el score experimental a `scoring.py`.

### `src/annotations.py`

Lee etiquetas manuales con `timestamp` o `seconds_elapsed`. Para cada anotación busca el evento más cercano dentro de ±5 segundos.

El comparador V0 es exploratorio. Una evaluación académica posterior debería imponer emparejamiento uno a uno para evitar que el mismo evento detectado explique varias anotaciones.

### `src/maps.py`

Crea un mapa Folium con:

- trayectoria GPS azul;
- segmentos verdes, amarillos o rojos;
- eventos coloreados por severidad;
- capas activables y tooltips.

Usa teselas públicas y no requiere una API comercial. Para uso masivo deberá revisarse la política del proveedor de teselas o desplegar infraestructura cartográfica propia.

### `src/analyzer.py`

Es la fachada principal del sistema. `TripAnalyzer.analyze` ejecuta las etapas en orden y devuelve `AnalysisResult`. `TripAnalyzer.export` produce CSV y JSON reproducibles.

Este archivo define el límite arquitectónico más importante: una futura API debería llamar a `TripAnalyzer`, no copiar lógica desde Streamlit.

### Archivos de `tests/`

- `test_loader.py`: crea ZIP sintéticos, comprueba detección de sensores, columnas, metadata horaria y ausencia de GPS.
- `test_quality.py`: verifica frecuencia real, cortes artificiales y coordenadas GPS inválidas.
- `test_detector.py`: genera ruido reproducible, gravedad e impacto artificial para probar preprocesamiento, detección y agrupación.
- `test_gps.py`: comprueba asociación temporal, tolerancia, conversión de velocidad y distancia Haversine.
- `test_analyzer.py`: ejecuta el pipeline completo, exporta a un directorio temporal y prueba anotaciones manuales.

Los tests no demuestran validez científica del detector. Demuestran que el software cumple comportamientos técnicos conocidos y que cambios futuros no rompen silenciosamente el pipeline.

## 6. Por qué se usa cada librería

| Librería | Motivo |
|---|---|
| `numpy` | Operaciones vectorizadas, álgebra, estadística, magnitudes y Haversine |
| `pandas` | Lectura CSV, limpieza, series temporales, ventanas tabulares y exportación |
| `scipy` | Diseño y aplicación estable de filtros Butterworth |
| `streamlit` | Prototipo interactivo rápido para inspección y demostración |
| `plotly` | Gráficos interactivos de aceleración y giroscopio |
| `folium` | Mapas Leaflet sin depender de una API comercial pagada |
| `streamlit-folium` | Integración del mapa Folium dentro de Streamlit |
| `pytest` | Pruebas automáticas reproducibles con señales sintéticas |

La biblioteca estándar también es importante:

- `zipfile`: inspección segura de archivos ZIP;
- `pathlib`: rutas portables y explícitas;
- `dataclasses`: contratos de datos y configuración;
- `logging`: trazabilidad operativa;
- `hashlib`: identificación estable de archivos subidos;
- `json`: reportes reproducibles.

## 7. Qué está científicamente fundamentado y qué sigue experimental

### Fundamentos establecidos

- cálculo de magnitud vectorial;
- frecuencia basada en diferencias temporales;
- filtros digitales Butterworth;
- filtrado de fase cero para análisis offline;
- RMS, varianza, percentiles y factor de cresta;
- MAD e IQR como estadísticas robustas;
- distancia geodésica Haversine;
- separación entre datos RAW y derivados;
- validación con señales sintéticas y recorridos independientes.

### Decisiones experimentales del V0

- ventana de 0.5 segundos;
- solapamiento del 50 %;
- frecuencias de corte 0.35 y 12 Hz;
- pesos del score;
- umbral 3.5;
- unión de eventos a 1 segundo;
- tolerancia GPS de 2 segundos;
- categorías de severidad;
- segmentos de 20 metros;
- fórmula y límites del `road_condition_score`.

No es incorrecto usar parámetros experimentales en un prototipo. Lo importante académicamente es declararlos, registrar su valor, justificar la hipótesis y validarlos posteriormente.

## 8. Variables que pueden confundir al detector

La señal no depende únicamente del pavimento. También influyen:

- modelo y sensibilidad del teléfono;
- ubicación y fijación del dispositivo;
- orientación y movimiento dentro del vehículo;
- velocidad del vehículo;
- suspensión, neumáticos y presión;
- tipo y carga del vehículo;
- frenado, aceleración y curvas;
- lomos, tapas, juntas, ripio y eventos que no son deterioro;
- precisión y frecuencia del GPS;
- clima y condiciones de conducción.

Por eso un pico alto no equivale automáticamente a un bache ni a una vía en mal estado.

## 9. Plan académico de validación

### Etapa 1: protocolo de captura

Definir posición del teléfono, soporte, vehículo, presión de neumáticos, ruta, sentido, velocidad objetivo y condiciones climáticas. Registrar cualquier desviación.

### Etapa 2: verdad de terreno

Crear anotaciones con al menos:

- tipo de irregularidad;
- instante o intervalo;
- coordenada revisada;
- severidad observada con una rúbrica definida;
- confianza del anotador;
- evidencia fotográfica o video cuando sea posible.

Idealmente dos evaluadores deberían anotar una parte de los recorridos para medir concordancia.

### Etapa 3: evaluación de detecciones

Con emparejamiento temporal uno a uno se pueden calcular:

$$
Precisión=\frac{TP}{TP+FP}
$$

$$
Recall=\frac{TP}{TP+FN}
$$

$$
F1=2\frac{Precisión\cdot Recall}{Precisión+Recall}
$$

También conviene informar falsos positivos por kilómetro y error espacial de localización.

### Etapa 4: análisis de sensibilidad

Variar sistemáticamente ventana, filtros, umbral y unión de eventos. Elegir parámetros usando recorridos de desarrollo y confirmar el resultado en recorridos separados.

Nunca se debe seleccionar un umbral y reportar su rendimiento sobre exactamente los mismos datos usados para elegirlo.

## 10. Camino hacia Machine Learning

ML debe incorporarse después de construir un conjunto de datos etiquetado y confiable.

### Unidad de aprendizaje

Cada fila podría ser una ventana con:

- características actuales;
- velocidad y precisión GPS;
- características por eje en el marco del vehículo;
- espectro o potencia por bandas de frecuencia;
- giroscopio y orientación;
- etiqueta `NORMAL`, `BACHE`, `LOMO`, `JUNTA`, etc.;
- identificadores de recorrido, vehículo, teléfono y conductor.

### Prevención de fuga de datos

La separación de entrenamiento y prueba debe hacerse por recorrido, ruta o día, no mezclando ventanas vecinas del mismo viaje en ambos conjuntos. Ventanas solapadas son muy parecidas y producirían resultados artificialmente altos.

### Modelos iniciales razonables

Antes de redes neuronales conviene comparar:

1. detector robusto V0 como línea base;
2. regresión logística;
3. árbol o Random Forest;
4. gradient boosting;
5. modelos temporales solo si el volumen y la calidad de etiquetas lo justifican.

La elección final debe basarse en validación, interpretabilidad, costo computacional y capacidad de ejecutar en Android.

## 11. Hoja de ruta tecnológica

### V0 actual: análisis offline

```text
ZIP -> TripAnalyzer -> CSV/JSON/HTML -> Streamlit
```

Objetivo: entender datos, comprobar hipótesis y formar un conjunto de validación.

### V1: calibración y comparación de recorridos

- interfaz de anotación integrada;
- emparejamiento uno a uno;
- métricas por recorrido y kilómetro;
- versión del algoritmo en cada reporte;
- identificación de teléfono, vehículo y montaje;
- comparación de recorridos repetidos sobre la misma ruta.

### V2: modelo de datos persistente

- PostgreSQL para recorridos, dispositivos y resultados;
- PostGIS para geometrías, eventos y segmentos;
- almacenamiento de RAW fuera de la base o en objetos;
- hashes para integridad y deduplicación;
- migraciones de esquema y auditoría.

### V3: API de procesamiento

```text
Android -> FastAPI -> cola de trabajos -> TripAnalyzer -> PostgreSQL/PostGIS
```

La API recibiría archivos o lotes, validaría autenticación y formato, crearía un trabajo y procesaría fuera de la petición HTTP. `TripAnalyzer` puede reutilizarse, pero deberá aceptar también streams o referencias de almacenamiento.

### V4: captura Android

- servicio de captura con permisos explícitos;
- reloj monotónico común entre sensores;
- almacenamiento local tolerante a desconexiones;
- envío por lotes y reintentos;
- metadatos de dispositivo y montaje;
- control de consumo energético;
- consentimiento, privacidad y minimización de ubicación.

### V5: plataforma operativa

- dashboard web multiusuario;
- mapas por fecha, ruta y confianza;
- agregación de múltiples pasadas;
- detección de cambios en el tiempo;
- monitoreo, métricas y alertas de fallos;
- versionado de datos, características y modelos.

## 12. Mejoras técnicas recomendadas

### Corto plazo

- agregar una interfaz de anotación en Streamlit;
- exportar ventanas y características a Parquet;
- incluir gráficos de distribución y espectro;
- probar distintas velocidades y fijaciones del teléfono;
- registrar una versión del pipeline y un hash del ZIP;
- añadir pruebas con archivos corruptos, columnas alternativas y viajes muy cortos.

### Mediano plazo

- usar orientación para proyectar la aceleración al marco vertical del vehículo;
- interpolar GPS únicamente con una política explícita y cuantificar incertidumbre;
- normalizar características por bandas de velocidad;
- agregar densidad de eventos por kilómetro;
- usar geometrías reales de cada segmento en lugar de solo sus extremos;
- comparar varias pasadas antes de clasificar un tramo.

### Largo plazo

- aprendizaje supervisado con validación por recorrido;
- estimación de incertidumbre y calibración de probabilidades;
- inferencia en el teléfono cuando sea técnicamente conveniente;
- integración con inventarios viales o inspección profesional;
- estudio de correlación con métricas viales reconocidas, sin afirmar equivalencia antes de validarla.

## 13. Cómo estudiar el proyecto en orden

Para comprender el código sin perderse, se recomienda leerlo así:

1. `src/config.py`: conocer los parámetros.
2. `src/loader.py`: entender la forma de los datos.
3. `src/quality.py`: revisar cuándo un viaje es utilizable.
4. `src/preprocessing.py`: seguir la transformación de la señal.
5. `src/features.py`: ver cómo una serie se convierte en filas de características.
6. `src/detector.py`: comprender el score y la agrupación.
7. `src/gps.py`: seguir la georreferenciación.
8. `src/segmentation.py` y `src/scoring.py`: estudiar el estado por tramos.
9. `src/analyzer.py`: observar cómo se conecta todo.
10. `src/maps.py` y `app.py`: revisar finalmente la presentación.

Las pruebas en `tests/` muestran ejemplos pequeños y controlados de cada comportamiento. Son un buen punto de entrada para experimentar sin depender de los recorridos reales.

## 14. Idea central para el futuro

El valor principal del V0 no es solo el mapa final. Es haber creado un pipeline reproducible que separa:

- captura;
- calidad;
- transformación de señal;
- detección;
- georreferenciación;
- agregación espacial;
- presentación.

Esa separación permite reemplazar una parte sin reconstruir todo el sistema. El siguiente salto académico no debería ser agregar inmediatamente un modelo complejo, sino obtener mejores anotaciones, repetir recorridos controlados y medir de forma honesta cuándo el detector acierta, falla o confunde una maniobra con una irregularidad real.
