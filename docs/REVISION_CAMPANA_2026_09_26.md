# Revision de captura, etiquetas y evaluacion por corredor

Actualizacion posterior: Pablo aclaro que marcaba 2-3 segundos despues del
impacto, tras percibir estabilizacion. Se repitio el experimento con retraso
de 2.5 s; ver [comparacion controlada](PRUEBA_RETRASO_2_5_SEGUNDOS.md).
Las observaciones y cifras siguientes corresponden a la revision anterior;
un pico fuera de su ventana no equivale a una anotacion incorrecta.

## Alcance y evidencia

Revision del 26 de septiembre de 2026: foto referencia.jpeg aportada por Pablo,
su descripcion de captura, auditoria numerica de las 39 marcas BACHE y 117
NORMAL candidatas y lectura visual de sus 11 laminas de magnitud de aceleracion.
No se inspecciono el pavimento ni se dispuso de video sincronizado. Esta revision
de senales NO confirma la causa fisica de los impactos ni valida etiquetas NORMAL.
No se cambiaron etiquetas, parametros de ventanas ni archivos RAW.

Ejecucion reproducible de referencia:
[informe y metricas](../outputs/reports/campana_2026_09_25/20260926T141000184380Z/INFORME_PILOTO.md).
[Tabla por ventana](../outputs/reports/campana_2026_09_25/20260926T141000184380Z/revision_senales.csv).
Los artefactos bajo outputs no se versionan automaticamente en Git.

## 1. Captura y montaje

Confirmado por el participante: ambas apps funcionaban en el mismo smartphone;
Anotador Vial era una ventana flotante sobre Sensor Logger; Pablo, como
acompanante, pulsaba las anotaciones. Se utilizo el mismo soporte durante
los tres recorridos, mas suelto en Prieto Norte y mas ajustado en los otros dos.
La foto muestra el telefono vertical, sujeto en un soporte cerca del tablero.
La foto no permite medir rigidez, vibracion ni ejes respecto de la gravedad.

Este montaje permite registrar senales y marcas simultaneas; compartir telefono
facilita el uso de epoch del mismo reloj, pero no elimina retraso de reaccion
humana ni latencia de entrega de muestras. Pulsar la pantalla podria introducir
movimiento: no se ha medido ese efecto ni debe afirmarse que explica un pico.

**Limitacion central:** ruta y firmeza del soporte cambian juntas. No se puede
separar su efecto con esta campana. Conservar Prieto Norte, identificandolo como
montaje mas suelto; no excluirlo solo para mejorar metricas. El acelerometro
mide el movimiento del telefono, no directamente el perfil del pavimento.
No hay calibracion de la respuesta mecanica del conjunto vehiculo/soporte.

## 2. Revision de BACHE

Se observaron aumentos localizados de vibracion en varias marcas, por ejemplo
Monte Oscuro A002/A003/A030 y Las Mariposas A007/A013/A023. Tambien hay ventanas
con varios picos o vibracion sostenida; el maximo no siempre identifica un
impacto unico. Esto es compatible con eventos mecanicos, no prueba de baches.

La revision numerica utiliza el pico maximo en [-3,+1] s respecto del boton:

- 19/39 picos candidatos quedan fuera de la ventana fija centrada 1.5 s antes
  del boton (ventana de 1.5 s). No significa que las 19 marcas sean erroneas.
- 5/39 quedan a <=0.15 s de un borde de la busqueda. El intervalo puede estar
  recortando la vibracion de interes; ampliar la busqueda requiere revision,
  no optimizacion mirando el F1 del test.
- 2/39 maximos se ubican despues del boton: Prieto Norte A002 y Las Mariposas A010.
- Las Mariposas A017 tiene un maximo a unos 0.047 s antes del boton. Es ambiguo:
  no permite distinguir contacto con pantalla, vibracion vial u otra causa.
- La mediana del retraso candidato es 1.986 s. NO es una estimacion validada del
  tiempo de reaccion: depende de elegir el maximo y del intervalo de busqueda.

Casos prioritarios de inspeccion temporal:

| Caso | Observacion de senal | Decision prudente |
|---|---|---|
| Prieto Norte A002 | Pico propuesto casi +1 s; en el contexto se ve un pico mayor antes de -3 s. | Alineacion ambigua; revisar contexto mas amplio sin reasignar automaticamente. |
| Prieto Norte A005 | Multiples picos antes del boton, no un unico transitorio aislado. | Mantener incertidumbre temporal. |
| Monte Oscuro A016/A029 | Maximos cerca del borde anterior de busqueda. | Revisar si se recorto un episodio. |
| Monte Oscuro A033 | En el contexto hay un pico posterior mayor que el candidato elegido. | No asumir que el maximo seleccionado corresponde al bache anotado. |
| Las Mariposas A003/A009 | Maximos cerca de -3 s. | Revisar contexto y posible episodio prolongado. |
| Las Mariposas A010/A017 | Maximo posterior o casi coincidente con pulsacion. | Solicitar evidencia externa antes de confirmar instante/causa. |

Los graficos muestran magnitud, no direccion vertical certificada. No se realizo
una auditoria visual exhaustiva de todos los ejes, espectros o cuaterniones.
Los HTML previos conservan ejes de aceleracion y magnitudes total/giroscopio
para ampliar la inspeccion de eventos individuales.

## 3. Revision de NORMAL

Se revisaron las 117 ventanas unicas; no se contaron dos veces por modalidad.
La mayoria muestra menor amplitud que las ventanas BACHE seleccionadas por pico,
pero esa comparacion esta sesgada por la propia seleccion de maximos BACHE.
No demuestra ausencia de defectos en los negativos.

Diez ventanas tienen un pico >= percentil 25 de los picos BACHE de su recorrido:
Monte Oscuro N003/N037/N057/N063 y Las Mariposas N004/N019/N022/N026/N032/N037.
Es una regla descriptiva para priorizar revision, NO un criterio de reclasificacion
o eliminacion. Se calculo sobre toda la campana, no se utilizo para entrenar,
seleccionar features ni modificar las metricas.

Monte Oscuro N063 y Las Mariposas N019/N022 muestran transitorios que merecen
revision externa. N003/N063 son ventanas vecinas del mismo contexto: tampoco
deben interpretarse como observaciones fisicas plenamente independientes.
Otros graficos muestran impactos fuera de la ventana usada para features, por
ejemplo Prieto Norte N006; no atribuir al negativo todo su contexto de 6 s.
La zona gris identifica la ventana efectiva de 1.5 s en las laminas finales.

Hay dos negativos de Las Mariposas con velocidad GPS <5 km/h: N025 (4.104) y
N036 (0). Una parada no certifica pavimento normal; conservar estos casos para
auditar y definir en el futuro una politica de velocidad antes de evaluar.

| Recorrido | Mediana pico NORMAL / BACHE (m/s2) | Mediana velocidad NORMAL / BACHE (km/h) |
|---|---:|---:|
| Prieto Norte | 3.50 / 9.87 | 44.50 / 26.86 |
| Monte Oscuro | 4.03 / 11.10 | 36.88 / 23.63 |
| Las Mariposas | 4.03 / 10.52 | 34.02 / 21.74 |

La velocidad tambien difiere por etiqueta. Como el bosque la utiliza, podria
aprender el comportamiento de conduccion ademas de la vibracion. Una futura
comparacion con/sin velocidad y por bandas de velocidad debe planificarse antes
de la siguiente evaluacion, sin elegir la variante mirando estos tests.

## 4. Evaluacion agrupada por corredor

Se anadio corridor_id al manifiesto y dataset. Monte Oscuro y Las Mariposas se
mantienen juntas en cada fold Leave-One-Corridor-Out (LOCO). Prieto Norte forma
el otro grupo, aunque comparte sectores; por eso se conserva la purga espacial
de entrenamiento a 50 m de las fijaciones GPS del grupo de test.

F1 de Random Forest; ver informe para precision, recall, umbral y matrices:

| Test | Modalidad | Sin purga | Con purga | Train sin/con purga |
|---|---|---:|---:|---:|
| Ida y vuelta juntas | Retraso fijo | 0.652 | 0.598 | 16 / 12 |
| Ida y vuelta juntas | Asistida por pico | 0.756 | 0.706 | 16 / 12 |
| Prieto Norte | Retraso fijo | 0.400 | 0.667 | 140 / 118 |
| Prieto Norte | Asistida por pico | 0.857 | 1.000 | 140 / 118 |

Solo hay dos grupos; Prieto Norte aporta cuatro positivos y un montaje distinto.
El F1=1.000 en un fold pequeno no acredita un detector perfecto. Las dos
modalidades dependen de anotaciones para proponer ventanas positivas, y la
asistida por pico usa informacion de la etiqueta para centrar el impacto.
No se calculan FP/km ni se declara deteccion continua validada.

## 5. Decision y siguiente incremento

La campana sirve para demostrar captura, sincronizacion, extraccion, revision y
evaluacion exploratoria en Etapa 2. No es necesario desecharla. Su principal
aporte es identificar problemas del protocolo antes de recolectar mas datos.

1. Mantener el soporte firme y registrar su estado antes de cada sesion; repetir
   Prieto Norte con montaje ajustado para estudiar esa diferencia sin cambiar ruta.
2. Caracterizar por separado las pulsaciones con el vehiculo detenido; no asumir
   que esa prueba por si sola explica lo observado durante la marcha.
3. Recoger recorridos de corredores nuevos, sin usarlos para ajustar el piloto.
4. Confirmar causas e instantes con evidencia externa segura, y registrar tramos
   CAMINO_MALO con inicio/fin. Mantener como inciertos los casos no verificables.
5. Evaluar despues deteccion continua con matching uno a uno; reservar un conjunto
   final y no eliminar negativos dificiles para aumentar el F1.

## Implementacion y comprobacion

`src/pilot/review.py` exporta revision_senales.csv y 11 laminas PNG de muestras
nativas. Las reglas de revision no alteran el dataset. `evaluation.py` acepta
agrupacion por corredor y concatena las trazas de ida/vuelta para la purga.
El informe nuevo incluye LORO y LOCO; los resultados anteriores se conservaron.
Pillow genera graficos locales sin navegador ni servicio externo.

Verificado: 21 pruebas aprobadas, incluidos tests de separacion por corredor y
conservacion de etiquetas. SHA-256 de las seis entradas y del codigo coinciden
con provenance.json de la ejecucion. Datos de captura declarados por el usuario
quedan registrados en capture_context del manifiesto. No se hizo commit ni push.
