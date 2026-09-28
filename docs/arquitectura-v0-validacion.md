# Registro del diagrama V0

- diagram_type: architecture
- output: arquitectura-v0.html
- specification: arquitectura-v0.json
- specification_sha256: 97882094a50a5b09330589f098073b03fdad4c3d3bbb20fecbd86b08ac40f9a7
- artifact_sha256: fa9d108e7177fb31027a3145020186e49ac4f10c0d11793d90e1f5895af60c1e
- validation: 9/9 showcase, 0 errors, 0 warnings
- browser_evidence: passed
- visual_review: passed
- correction_rounds: 1

Inspeccion automatica: Chrome, 1440x900, 1600x1000, 1920x1080 y
2048x1320. Revision visual de capturas: claro a 2048x1320 y oscuro
a 1440x900. Sin solapamientos visibles entre nodos y relaciones.
El recibo automatico conserva visualReview: pending porque no representa
la revision visual posterior realizada aqui.

Fuentes locales inspeccionadas: app.py, src/analyzer.py y src/maps.py.
Vista agrupada de componentes; las flechas desde TripAnalyzer representan
llamadas a modulos, no servicios independientes. Los resultados son archivos
locales, aunque el visor los clasifica visualmente como almacenamiento.
Los graficos Plotly se construyen en app.py y el mapa Folium en src/maps.py.
La secuencia interna se explica en las notas del diagrama.
Los controles del visor y su atributo HTML lang usan ingles por limitacion
del renderer; el contenido del proyecto esta escrito en espanol.

Abrir arquitectura-v0.html directamente en un navegador. No requiere Streamlit.
