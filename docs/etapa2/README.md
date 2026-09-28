# Etapa 2: paquete de diseno y trazabilidad

Version de trabajo revisada: 2026-09-27. Entrega prevista: 2026-10-02.
Estado: borrador tecnico revisable; no aprobacion del profesor ni cierre del backlog.

## Entregables

1. [Diseno tecnico](DISENO_TECNICO.md): limites, modelo logico, flujos, estados, decisiones y pruebas de aceptacion.
2. [Contrato de datos y relojes](CONTRATO_DATOS.md): entradas actuales, propuesta de exportacion y validacion.
3. [Backlog trazable](BACKLOG.md): las 26 HU y 18 tareas originales, evidencia y trabajo pendiente.
4. [Protocolo experimental](PROTOCOLO_EXPERIMENTAL.md): captura, etiquetado retrospectivo, repetibilidad y evaluacion.
5. [Ficha de sesion](FICHA_SESION.json): plantilla propuesta; null significa dato desconocido, no un valor confirmado.
6. [Diagnostico Android y alcance integrado](DIAGNOSTICO_ANDROID_Y_ALCANCE.md): arquitectura observada, riesgos, archivos afectados e incrementos de captura propia vinculados con Etapa 1.
7. [Primer incremento Android A1a](IMPLEMENTACION_ANDROID_A1.md): cambios aplicados, respaldo, ocho pruebas unitarias y limites pendientes.
8. [Captura IMU Android A2](IMPLEMENTACION_ANDROID_A2.md): sensores propios, escritura asincrona, ZIP, pruebas y limites de aceptacion.
9. [Interfaz Android B1](IMPLEMENTACION_ANDROID_B1.md): navegacion, historial de archivos, detalle, eventos y preferencias; aceptacion visual pendiente.
10. [Sensores y GPS A3](IMPLEMENTACION_ANDROID_A3.md): gravedad, aceleracion lineal, rotacion, GPS, permisos y esquema capture-preview-2; aceptacion fisica pendiente.
11. [Primera captura propia revisada](REVISION_CAPTURA_PROPIA_20260927_204012.md): cinco sensores y GPS en dispositivo; tiempos y archivos consistentes, observaciones GPS y prueba de marcas pendiente.
12. [Revision de cierre](REVISION_CIERRE_ETAPA2.md): contraste con PDF original, brechas verificadas, decisiones y orden de cierre. Integracion Android-PC aun no validada.

Fuentes: informe de Etapa 1 de Pablo, pp. 11-12, 16-21, 27-35 y 36-41;
codigo Python de este repositorio; lectura acotada de MainActivity.kt y
OverlayService.kt de AnotadorVial; declaraciones del participante y campana real.
El paquete inicial solo documentaba el diseno. Los incrementos A1a/A2/A3/B1 posteriores
modificaron y compilaron Android. Hay pruebas JVM y una captura fisica corta auditada;
la aceptacion completa y la integracion con Python siguen pendientes.
No se modificaron los RAW de campana, etiquetas ni modelos en estos incrementos.
Los documentos distinguen comportamiento actual y destino.

## Evidencias existentes

- [Arquitectura V0](../arquitectura-v0.html) y [propuesta](../arquitectura-etapa2-propuesta.html): previas al nuevo modulo piloto; no cubren por si solas todo el diseno.
- [Documentacion tecnica](../../DOCUMENTACION_TECNICA.md).
- [Campana piloto](../CAMPANA_PILOTO_2026_09_25.md).
- [Revision de montaje y senales](../REVISION_CAMPANA_2026_09_26.md).
- [Prueba del retraso de anotacion](../PRUEBA_RETRASO_2_5_SEGUNDOS.md).
- [Pruebas](../../tests/test_pilot.py) y [lanzador](../../run_tests.py).

Los resultados bajo outputs son evidencia local ignorada por Git. Antes de
entregar, conservar un conjunto de evidencia revisado sin publicar ubicaciones
sensibles indiscriminadamente. No basta enlazar archivos que el evaluador no recibe.

## Relacion con la rubrica

| Peso | Aporte de este paquete | Cierre pendiente |
|---|---|---|
| 20 % retroalimentacion | Se conserva separacion entre feedback del profesor y hallazgos propios. | Adjuntar correo y fecha; confirmar tratamiento de feedback sin correcciones. |
| 10 % avance del diseno | Inventario completo HU/T, subtareas D y criterios de cierre. | Acordar linea base de diseno y revisar cada evidencia; no declarar 100 % aun. |
| 55 % calidad | Modelo, contratos, errores, decisiones y protocolo conectados con requisitos. | Revision de consistencia; diagramas actualizados y validacion de contratos contra implementacion futura. |
| 15 % documentacion | Documentos enlazados y separacion actual/propuesto. | Informe final, cambios versionados, evidencia empaquetada y revision Git. |

## Revision que requiere Pablo

- Confirmado por Pablo: Xiaomi Mi 10T, Android 12, compilacion SKQ1.211006.001. ADB y metadata posterior identifican M2007J3SY; la captura propia declara Android 12. Vehiculo y version exacta de APK desplegada siguen por documentar.
- Revisar la ficha y el procedimiento de la siguiente captura; fijar tramo, sentido y disponibilidad de repeticiones.
- Revisar las desviaciones Room/CSV, Fused/LocationManager y perfil provisional, sin presentar captura propia y Python como flujo integrado ya validado.
- Revisar las subtareas D y su relacion con el backlog original antes de usarlas como denominador de avance.
- Resolver con el profesor la prioridad de OE5: la p. 29 lo trata como extension, pero sigue en los objetivos generales del proyecto.

## Secuencia de cierre

Primero revisar contrato y modelo; despues acordar backlog y protocolo; finalmente
actualizar diagramas, ejecutar pruebas de aceptacion pertinentes y consolidar informe.
La revision del borrador no necesita esperar a una nueva campana. La validacion
experimental final si necesita evidencia independiente.
