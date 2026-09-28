# Arquitectura propuesta de Etapa 2

Vista simplificada de componentes y flujo principal; no es inventario de servicios desplegados ni diagrama completo de interfaces.
Fuentes revisadas: README.md, src/analyzer.py y la revision previa de MainActivity.kt, OverlayService.kt y AndroidManifest.xml de AnotadorVial.
Importacion central, PostgreSQL/PostGIS y persistencia de ejecuciones son propuestas.
La importacion tambien debera registrar sesiones, archivos y anotaciones en la base; el panel consultara el historial mediante la capa de aplicacion. Esas relaciones secundarias no se dibujan.
FastAPI sera la interfaz de servicio prevista, aun no implementada. No se asume carga automatica desde Sensor Logger.

diagram_type: architecture
output: C:/Users/GOMEPAB/Desktop/Protipo V0/docs/arquitectura-etapa2-propuesta.html
specification_sha256: 217a80628d32d4c9bafd3bc0a2e90e883f9e6d711e037f0bc749638203d9fe82
artifact_sha256: 101e447e1a4f756b7555a062d2bb82c00b062e1e3bac8c18fa8b4433676fc52a
validation: 9/9 showcase, 0 errors, 0 warnings
browser_evidence: passed
visual_review: passed
correction_rounds: 2

El comprobador automatico verifico 1440x900, 1600x1000, 1920x1080 y 2048x1320 sin desbordamiento. Revision visual de capturas: 1440x900 claro y 2048x1320 oscuro; nodos, flechas y etiquetas legibles sin solapamiento visible. No se probaron manualmente todas las funciones interactivas ni exportaciones.
Contenido redactado en espanol; controles fijos del visor y html lang usan ingles por limitacion del renderer.
