# Contexto de traspaso: Etapa 3 (borrador inicial)

> Actualizacion 09/10/2026: este texto se conserva como nota historica del 28/09.
> El estado y plan actuales estan en [BACKLOG.md](BACKLOG.md),
> [EVIDENCIAS.md](EVIDENCIAS.md) y [PLAN_TRABAJO.md](PLAN_TRABAJO.md).
> La lectura nativa ya funciona para inspeccion; continuidad y deteccion siguen
> pendientes. Entrega confirmada: 30/10/2026. Los precios y afirmaciones de
> proveedores de esta nota no se han revalidado para contratar un servicio.

Creado: 28 de septiembre de 2026, durante el cierre de Etapa 2. No es un compromiso
aprobado por el profesor guía ni una planificación formal de Etapa 3; es una nota
de traspaso para no perder decisiones y alternativas discutidas mientras se prioriza
la entrega del 2 de octubre de 2026.

## 1. Por qué existe este documento

Durante el cierre de Etapa 2 surgió la idea de exponer el nucleo de analisis (V0 /
TripAnalyzer) como un servicio accesible por red, en vez de un flujo manual de
exportar ZIP -> copiar a PC -> analizar. Se decidio explicitamente **no** perseguir
esto antes del 2 de octubre de 2026, para no comprometer el tiempo disponible para
resolver R-01 (adaptador Android-PC, ver `../etapa2/REVISION_CIERRE_ETAPA2.md`) y la
prueba de confiabilidad de la captura propia. Queda registrado aqui para retomarlo
cuando OE5 pase de "extension de plataforma" (Seccion 8.4 del informe de Etapa 1) a
un compromiso activo de implementacion.

## 2. Idea evaluada

Empaquetar el pipeline existente (TripAnalyzer / src/pilot) detras de una API
(FastAPI) corriendo en Docker, con un mapa web (Leaflet) que muestre recorridos,
eventos y baches detectados a partir de los datos procesados. En una version
posterior, la APK Android podria enviar sus datos directamente por red a esa API,
en lugar de solo exportar un ZIP local.

Esto corresponde directamente a OE5, HU-20 (persistencia central), HU-21 (API) y a
la subtarea de diseno D-09 del backlog de Etapa 2 (`../etapa2/BACKLOG.md`), que ya
estan marcadas como **N** (no evidenciado) o **parcial** y explicitamente fuera del
nucleo minimo evaluable segun la Seccion 8.4 del informe de Etapa 1.

## 3. Dos capas distintas, no confundir

1. **Que el servicio este accesible desde afuera de la PC de Pablo.** Hoy Docker en
   una PC personal no es alcanzable desde internet por defecto: NAT/CGNAT del
   proveedor, firewall de la red (casa o universidad), IP dinamica, y Android
   bloqueando HTTP sin cifrar desde la version 9 en adelante.
2. **Que la APK realmente mande datos por red.** Hoy el Android solo exporta ZIP a
   disco; no existe codigo de subida HTTP, manejo de reintentos ni de fallas de
   conexion. Es trabajo nuevo, no una desviacion de algo ya implementado.

Ambas capas deben resolverse para tener "cualquier dispositivo manda datos en
cualquier momento"; ninguna de las dos esta resuelta hoy.

## 4. Alternativas de despliegue evaluadas (costo / complejidad)

| Opcion | Costo aproximado | Complejidad | Aporta | Limite principal |
|---|---|---|---|---|
| Tunel (Cloudflare Tunnel / ngrok) sobre Docker local | Gratis | Muy baja; un comando sobre el Docker ya construido | URL publica HTTPS al instante, resuelve el bloqueo HTTP de Android | Depende de que la PC de Pablo este encendida; URL no estable sin dominio propio |
| Railway | ~US$5/mes (plan Hobby) | Baja; despliegue casi directo del mismo Docker/compose; Postgres+PostGIS como addon | Servidor siempre disponible, base de datos gestionada | Gasto recurrente; ya no existe plan gratuito permanente |
| Render | Gratis con limites, o ~US$7/mes | Baja, similar a Railway | Igual que Railway | Plan gratuito "duerme" tras inactividad; cold start de 30-50 s |
| Fly.io | Capa gratuita pequena, luego por uso | Media; mas configuracion (fly.toml, regiones, volumenes) | Puede salir barato a uso bajo, mas control | Curva de aprendizaje mayor sin experiencia previa |
| VPS propio (Hetzner/DigitalOcean) | ~US$4-6/mes | Alta; administracion manual de servidor, HTTPS, seguridad | Control total | Carga de trabajo de sysadmin no justificada para este proyecto |

## 5. Decision preliminar (a confirmar al iniciar Etapa 3)

- Para una demo o prueba puntual: usar el tunel gratuito sobre el mismo Docker que
  ya se evaluo para envolver TripAnalyzer con FastAPI y un mapa Leaflet.
- Para un despliegue sostenido en Etapa 3, si OE5 se confirma como compromiso activo
  con el profesor guia: Railway es la opcion con mejor relacion costo/complejidad,
  porque el mismo Docker/compose usado localmente se traduce casi directo a su
  despliegue, y ofrece Postgres/PostGIS gestionado sin administracion manual.
- No se ha decidido nada de esto con el profesor guia. No se declara compromiso de
  fecha ni de alcance; queda sujeto a la prioridad real que tenga OE5 en Etapa 3 y a
  si conviene mantenerlo como extension opcional o como nucleo evaluable.

## 6. Trabajo pendiente antes de poder avanzar esto en serio

Ninguno de estos puntos esta hecho; se listan para no reabrir la discusion desde
cero en Etapa 3:

- Resolver R-01 (adaptador Android-PC) y validar la confiabilidad de la captura
  propia; sin eso, cualquier API/mapa mostraria datos mal interpretados.
- Disenar el contrato de subida HTTP desde la APK (autenticacion minima, manejo de
  reintentos, subida parcial/fallida, tamano maximo de paquete) antes de programar
  cualquier codigo Android de red.
- Definir el modelo de persistencia central ejecutable (DDL/migraciones de
  PostgreSQL/PostGIS), hoy solo existe como modelo logico en
  `../etapa2/DISENO_TECNICO.md` seccion 2.
- Acordar con el profesor guia si OE5 se mantiene como extension de plataforma o
  pasa a ser exigible dentro del nucleo de Etapa 3, dado que la p. 29 del informe de
  Etapa 1 lo trata como extension pero sigue vigente en los objetivos generales.

## 7. Referencias

- Rubrica y estructura general de Etapa 2: `../../CONTEXTO_ETAPA_2.md`.
- Diseno tecnico vigente (limites, modelo logico, ADR): `../etapa2/DISENO_TECNICO.md`.
- Backlog trazable y subtareas de diseno D-01 a D-10: `../etapa2/BACKLOG.md`.
- Hallazgos de cierre de Etapa 2 (R-01 a R-05): `../etapa2/REVISION_CIERRE_ETAPA2.md`.
