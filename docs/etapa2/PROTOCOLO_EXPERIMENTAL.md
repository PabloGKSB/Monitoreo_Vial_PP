# Protocolo experimental de captura y evaluacion

Version propuesta PE-0.2, revision de coherencia 2026-09-27. Para aceptar antes de nueva campana.
No se atribuye retrospectivamente su cumplimiento a sesiones del 25/09.
Trazabilidad: OE3/OE6, HU08-09/16-17/23-26, RE01-13, R02/07/08/09/10.

## 1. Campana existente y semantica

Tres sesiones, dos grupos de corredor: Prieto Norte; Monte Oscuro ida y Las
Mariposas vuelta. Mismo smartphone y soporte; mas suelto en Prieto Norte, mas
ajustado en las otras. Pablo anotaba como acompanante mediante overlay sobre
Sensor Logger. Esperaba estabilizacion percibida, aproximadamente 2-3 s despues
del impacto. Confirmacion posterior de Pablo: Xiaomi Mi 10T, Android 12,
compilacion SKQ1.211006.001. Vehiculo y versiones desplegadas de apps pendientes;
no se verifico el equipo por ADB.

BACHE significa "evento reportado retrospectivamente por el observador".
Hora del boton no es hora del impacto. El retraso es una estimacion del operador,
no medicion exacta. La estabilizacion percibida no prueba que todos los picos
anteriores correspondan al mismo defecto. Marcas y waveform se conservan separadas.
La foto verifica disposicion aproximada, no rigidez ni orientacion numerica.

## 2. Preparacion de siguiente captura

Completar [ficha](FICHA_SESION.json) por sesion. Mantener codigo de vehiculo,
modelo telefono, Android/app/version, soporte/posicion, operador, sentido y ruta.
No registrar matricula ni nombres de terceros. Para repetir, definir tramo y
sentido antes de salir; propuesta de 4-5 pasadas bajo condiciones similares,
no requisito numerico de la rubrica ni garantia de suficiencia estadistica.

Con vehiculo detenido: verificar fijacion, almacenamiento/bateria disponibles,
sensores presentes, permisos, reloj y exportacion de prueba. Fotografiar montaje
sin rostros/matriculas. No configurar ni manipular el dispositivo al conducir;
anota el acompanante. No provocar impactos ni maniobras inseguras para medir.
Registrar velocidades observadas; no imponer una velocidad que comprometa seguridad.

Control de artefactos: probar pulsaciones separado de un recorrido, con telefono
fijo y vehiculo detenido; comparar periodos sin tocar y con marcas. El codigo
actual del anotador invoca vibrar(...,70) tras registrar eventos (MainActivity.kt
y OverlayService.kt). Eso es evidencia de una funcion, NO confirmacion de que la
APK usada en la campana activara el motor ni de que explique los picos observados.
Registrar configuracion/version y comprobar feedback haptico en la proxima prueba;
no mezclar configuraciones sin documentar el cambio. A2/A3 ahora suprime vibrar
mientras CaptureState esta ocupado, pero no controla otras apps. La descripcion
anterior corresponde al anotador previo, no prueba la conducta de la APK historica.

## 3. Captura y finalizacion

### Perfil legacy: Sensor Logger y anotador

1. Crear ficha e ID de pasada; iniciar Sensor Logger, comprobar IMU/GPS.
2. Iniciar Anotador; conservar MONITOREO_INICIO y origen de ambas sesiones.
3. Anotar evento despues de estabilizacion segun protocolo; no buscar un retraso
   exacto mientras se circula. Registrar posteriormente si hubo duda, multiples
   impactos o demora mayor. No inventar una marca individual para cada pico.
4. Si cambia el soporte o el telefono se mueve, registrar incidencia y dividir
   sesiones/condiciones cuando sea posible. No descartar datos sin dejar motivo.
5. Finalizar anotador y sensores; registrar bateria/bytes/duracion para RE13.
6. Exportar originales, calcular hashes y registrar pareja ZIP/CSV explicitamente.
7. Hacer copia de respaldo privada; solo derivados revisados en evidencia compartida.

### Perfil captura propia A3

1. Completar la misma ficha, indicando capture-preview-2, version APK/codigo y
   si se habilito GPS. Iniciar desde la app con vehiculo detenido.
2. Comprobar muestras y fijacion GPS reciente con precision informada; Disponible
   no significa coordenadas recibidas. Sin GPS, registrar la limitacion espacial.
3. Aplicar la misma semantica retrospectiva conservando hora real de pulsacion.
   Probar primero una marca OTRO y deshacer, sin simular defectos viales.
4. Finalizar, esperar cierre y exportar ZIP con seis CSV, metadata y anotaciones.
   Registrar bateria, bytes y montaje; no modificar RAW ni inventar datos ausentes.
5. Auditar fuera del lector legacy hasta tener adaptador propio validado. La prueba
   del 27/09 demuestra sensores/GPS y exportacion, pero no contiene marcas manuales.
6. Probar por separado pantalla apagada, permisos/rotacion y reapertura del historial.
   No atribuir continuidad garantizada a foreground ni equiparar prueba corta a campana.

## 4. Calidad y aceptacion de datos

ACCEPT = utilizable para el analisis declarado; REVIEW = incertidumbre que
requiere examen; REJECT = no utilizable para ese analisis. No borrar originales.
Registrar motivo, autor, fecha y criterio, independientemente de resultados ML.

| Condicion | Decision |
|---|---|
| Falta sensor exigido por esquema piloto o reloj absoluto fiable | REJECT para ese piloto; otros analisis posibles deben identificarse aparte. |
| Inicio/fin de monitoreo inconsistente | REJECT para construir etiquetas hasta resolver asociacion. |
| Soporte suelto/cambio de montaje | REVIEW; conservar como condicion distinta, no baseline de repetibilidad controlada. |
| Duplicados/retrocesos/gaps | Auditar antes de limpiar; investigar reloj y perdidas. |
| Ventana piloto con gap >0.1 s, cobertura <80 %, no finitos o borde incompleto | Excluir esa ventana y registrar motivo; valores experimentales, no norma. |
| Sin GPS dentro de 2 s | No georreferenciar; no inventar coordenadas. |
| GPS impreciso o salto sospechoso | REVIEW espacial; accuracy no es error medido contra terreno. |
| Solo señal sin evidencia independiente | No confirmar defecto fisico ni NORMAL por baja amplitud. |

No hay umbral de precision GPS ni F1 final acordado. Deben fijarse y justificarse
con datos de desarrollo ANTES de evaluar una nueva campana reservada. La etiqueta
QualityStatus de codigo no implementa por si sola toda esta politica.

## 5. Rubrica de revision de etiquetas

| Etiqueta/estado de revision propuesto | Evidencia necesaria | Uso |
|---|---|---|
| BACHE_REPORTADO | Marca original del operador | Candidato, no verdad confirmada. |
| BACHE_CONFIRMADO | Referencia externa suficiente y asociacion temporal/espacial revisada | Entrenamiento/evaluacion con version de etiqueta fijada. |
| NORMAL_REVISADO | Intervalo revisado independientemente y sin evento objetivo identificado | Negativo con alcance de inspeccion declarado. |
| OTRO_EVENTO | Evidencia de lomo, giro u otra causa | No convertir automaticamente en NORMAL. |
| AMBIGUO | Varios impactos posibles, desfase no resoluble o evidencia insuficiente | Mantener para revision, no forzar una clase. |

Estas categorias son diseño de revision; no reemplazan event_type de los CSV ni
han sido aplicadas como nuevas etiquetas de verdad. Registrar LabelRevision con
intervalo, evidencia, autor, fecha, confianza y razon; conservar revisiones previas.

Revision propuesta por marca: examinar contexto [-5,+2] s como ayuda visual,
usar [boton-3,boton-2] s como intervalo orientativo declarado, no limite fisico.
Contrastar evidencia externa, ejes/gyro y movimiento del soporte. Anotar comienzo,
final y dudas. Si hace falta ampliar contexto, registrar motivo, no optimizar
la ventana mirando F1. Un revisor adicional seria deseable; si no existe,
declarar revision por un solo observador y su limitacion.

CAMINO_MALO puntual no delimita todo un tramo. Registrar inicio/fin de tramos
en una revision externa antes de muestrear negativos definitivos. Mantener
negativos dificiles; no retirarlos por amplitud alta o por errores del modelo.

## 6. Analisis vigente y futuro

Vigente: dos experimentos fijos de 1.5 s, centrados 1.5 o 2.5 s antes del boton;
busqueda asistida por pico [-3,+1] s como modalidad separada. El nuevo retraso
es el punto medio declarado, no ajuste exhaustivo para maximizar test.
NORMAL se muestrea 1:3, semilla42, ventana completa fuera de +/-8 s de todas las
marcas; no demuestra ausencia de defectos. Todas las ventanas siguen provisionales.

Segmentacion por retorno a estabilidad: FUTURA. Antes de implementarla definir
senal/banda, baseline local, umbral, duracion minima de retorno, separacion de
episodios y manejo de gaps. Ensayar senales sinteticas con dos impactos, oscilacion
amortiguada, curvas y ruido; contrastar casos externos. No declarar que unir picos
proximos ya resuelve un mismo evento fisico.

## 7. Hipotesis de evaluacion

| Pregunta | Diseno | Que NO demuestra |
|---|---|---|
| Repetibilidad | 4-5 pasadas propuestas de mismo tramo/sentido/montaje, defectos de referencia identificados. Reportar por defecto/pasada, faltantes e incertidumbre. | Generalizacion a una calle nueva. |
| Otra pasada conocida | Separar sesiones completas, sin ventanas solapadas entre train/test. | Independencia geografica; puede repetir defectos. |
| Otro corredor | Mantener todas las pasadas/sentidos del corredor juntas; reservar corredor nuevo. | Robustez a nuevos telefonos/vehiculos sin ensayo adicional. |
| Montaje/velocidad | Variar una condicion a la vez cuando sea viable, registrar las demas. | Causalidad usando Prieto suelto frente a otra ruta firme. |

La campana actual ya fue explorada: desarrollo, no holdout final. LOCO con dos
grupos y purga50m es diagnostico, no validacion suficiente. Encajar imputacion,
normalizacion y seleccion de parametros solo en train. Versionar split y etiquetas.
No usar coordenadas, ID o retraso de anotacion como features predictoras.

Evaluacion futura continua: propuestas sin marcas de test; matching uno-a-uno
predefinido; precision/recall/F1 por clase, confusion, FP/km solo donde referencia
y distancia sean evaluables. Error espacial frente a referencia independiente;
repetibilidad por defecto fisico, no solo proximidad GPS. Informar n por grupo,
condiciones, exclusiones y denominadores. No fijar minimo F1 despues de ver test.

## 8. Condiciones para cerrar este diseno

Revisar con Pablo ficha, procedimiento y categorias; acordar tramo/sentido;
realizar una simulacion de registro/exportacion con metadata completa; comprobar
efecto haptico; registrar cambios de version. Una vez aceptado, congelar PE-0.2
para la siguiente campana. Hoy es borrador especificado, no protocolo ejecutado.
