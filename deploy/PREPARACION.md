# Preparativos de Monitoreo Vial

Fecha: 2026-10-18. Alcance: fuente y configuracion local; sin push, builds,
contrataciones, cambios Auth ni recursos remotos. Validaciones en una fase posterior.
Este documento conserva el corte de preparacion. La fase de validacion ya
esta en curso; consultar [VALIDACION.md](VALIDACION.md) para el estado actual.

## Fuente que se publicara

Remoto configurado: `PabloGKSB/Monitoreo_Vial_PP`; rama local `main`.
`release-files.txt` es la lista explicita del paquete de despliegue. Incluye
fuente Python, cliente web y lockfile, migraciones para ejecucion administrativa,
pruebas, scripts operativos, Dockerfile y documentacion de despliegue.
No incluye recorridos, capturas, APK, dependencias instaladas, resultados,
respaldos, cuentas de prueba ni variables privadas. La CA `.crt` es publica.

Preparar un paquete de fuente y un manifiesto con SHA-256, sin cambiar Git:

```powershell
.\.venv\Scripts\python.exe scripts/prepare_release.py
```

El resultado queda en `.api_local/deploy/FECHA-ID/source.zip` y `manifest.json`.
El escaneo detecta algunos formatos de secretos y no acredita una auditoria completa.
`.dockerignore` mantiene otra lista restrictiva para el contexto de imagen.

Hay dos ZIP de recorridos registrados en la historia de Git. Se retiraron
del indice con `git rm --cached`, conservando ambos archivos locales.
Esto los excluye de la siguiente version; los commits anteriores siguen
conteniendolos. No se reescribe ni se publica la historia durante esta etapa.
Un clon de este repositorio, incluso tras retirarlos, conserva ese riesgo.
El retiro sigue preparado en el indice; no hay commit ni push de estos cambios.

Para preparar el indice solo con la seleccion revisada:

```powershell
git add --pathspec-from-file=deploy/release-files.txt
git diff --cached --stat
```

El paquete y el indice son revisables antes del commit/push. No usar `git add .`.
El paquete no es un clon completo del proyecto Android ni de sus documentos.

## Entorno de construccion preparado

Este Windows no tiene Docker ni WSL instalados. Se prepara GitHub Actions con
`ubuntu-24.04`, Docker del runner y `linux/amd64`, sin instalar software de
sistema. El workflow actual `Validate container` acepta `workflow_dispatch` y
pull requests hacia main que cambien archivos de servidor/despliegue.
No usa secretos de produccion, no hace login
a registros de imagenes y no publica ni despliega.

Se ejecutara en la fase de validacion, despues de subir la fuente. Antes de
usarlo hay que revisar disponibilidad y presupuesto de Actions en GitHub;
no se ha verificado el plan ni el saldo de minutos de esa cuenta.
El job construye la imagen y registra su ID. La imagen queda en el runner
efimero: no se conserva como artefacto para el despliegue. La construccion
de Railway debe corresponder al mismo commit y revisarse despues.
Incluye un arranque y healthcheck sinteticos con SQLite aislado y red
deshabilitada. El arranque de produccion sigue requiriendo PostgreSQL TLS y
volumen persistente; ese camino no se sustituye por SQLite.

Alternativa en cualquier equipo Linux/Docker disponible:

```text
docker build --platform linux/amd64 -t monitoreo-vial:review .
```

Referencia: [Docker con GitHub Actions](https://docs.docker.com/build/ci/github-actions/).

## Servicio y capacidad propuestos, sin aprovisionar

| Ajuste | Propuesta inicial |
| --- | --- |
| Proyecto / servicio / entorno | Monitoreo Vial / monitoreo-vial / production |
| Fuente | Repositorio indicado, commit que supere la validacion |
| Construccion | Dockerfile en la raiz; sin secretos ni DSN en build args |
| Arranque | CMD de la imagen: python run_server.py |
| Procesos / replicas / regiones | 1 / 1 / 1, sin autoscaling |
| CPU / RAM maxima | 1 vCPU / 1 GB como punto de partida por validar |
| Almacenamiento | Volumen inicial de 5 GB montado en /data |
| Directorios | /data/archives; /data/backups solo para copia temporal |
| Healthcheck | /health, puerto PORT (8080 predeterminado) |
| Solapamiento | Sin despliegues simultaneos que escriban la misma base |
| Acceso inicial | Dos cuentas piloto existentes; nuevos registros deshabilitados |
| Originales | 30 dias; eliminacion manual condicionada al respaldo externo |
| Cuotas piloto | 20 trabajos y 32 MiB por cuenta / 24 h; reserva 512 MiB |

La RAM maxima es un limite, no una reserva ni una medicion de consumo.
La region se elegira junto con la region real de Supabase para reducir latencia;
todavia no esta decidida. No se creara otra base de datos en Railway.

Con dos cuentas a 256 MiB/dia durante 30 dias se acumulan unos 15 GiB: no
caben en Hobby. La propuesta de 32 MiB reduce esa cifra a unos 1,9 GiB,
dejando sitio para una copia temporal y la reserva. Un volumen comercial
de 5 GB tiene aproximadamente 4,66 GiB. Los calculos no incluyen todos los
metadatos ni espacio temporal: revisar ocupacion diariamente y detener nuevas
cargas al llegar a 2 GiB de originales hasta exportar el respaldo.
Ese umbral de 2 GiB es un procedimiento del operador, no una cuota global
implementada. Una tercera cuenta o mas volumen diario requieren recalcular.
La cuota piloto no permite subir un archivo de 64 MiB; la prueba del maximo
se hara despues en un entorno separado con cuotas ajustadas.

## Plan confirmado y objetivo de gasto

El usuario confirma que ya tiene Hobby de US$5/mes, con US$5 de consumo
incluido; el exceso se suma. No se modificara el plan. La meta inicial es
mantener el piloto dentro del consumo incluido, pendiente de medirlo.
La confirmacion del usuario no acredita el consumo ni el estado de facturacion
que el conector no permite consultar.

Estimacion orientativa de recursos de contenedor, con las tarifas documentadas:

| Escenario mensual | RAM promedio | CPU promedio | Volumen facturado | Egreso | Consumo aproximado |
| --- | --- | --- | --- | --- | --- |
| Ligero | 0,25 GB | 0,05 vCPU | 2 GB | 5 GB | US$4,05; Hobby minimo US$5 |
| Mas actividad | 0,50 GB | 0,20 vCPU | 5 GB | 10 GB | US$10,25 |

Tarifas de referencia: RAM US$10/GB-mes, CPU US$20/vCPU-mes, volumen
US$0,15/GB-mes y egreso US$0,05/GB. Son ejemplos, no una cotizacion o consumo
medido. No incluyen impuestos, proveedor de respaldos, GitHub Actions ni
posibles cambios de plan en Supabase. Confirmar importe en el dashboard antes
de crear recursos. No se ha autorizado consumo adicional sobre el objetivo
de US$5 ni un plan nuevo.

Proponer alerta a US$4 y limite de Compute a US$5, si el dashboard permite ese
importe; no estan configurados. Revisar alli como se contabiliza el consumo
incluido antes de aplicar el limite. El corte apaga cargas de trabajo y
no es una garantia de factura total que incluya impuestos o almacenamiento
que siga facturandose. No habilitar Railway Agent para esta aplicacion.

Fuentes consultadas el 18 de octubre de 2026:
[planes y tarifas](https://docs.railway.com/pricing/plans),
[consumo incluido](https://docs.railway.com/pricing/understanding-your-bill),
[control de costos](https://docs.railway.com/pricing/cost-control).

## Variables y autenticacion

La plantilla publica es `.env.production.example`. El preparador local copia
solo SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY y VIAL_DATABASE_URL desde `.env`,
comprueba el nombre del rol y adapta la CA a `/app/deploy/prod-ca-2021.crt`.
Los demas valores provienen de la plantilla piloto; no copia credenciales de
cuentas, conexiones de migracion ni ajustes locales de Windows.

```powershell
.\.venv\Scripts\python.exe scripts/prepare_production_env.py
```

Salida privada: `.api_local/deploy/production.env`, excluida de Git y Docker.
No se imprimen valores ni se sobrescribe un archivo existente. No se ha
verificado la conexion con esos valores. Cargarlos luego como variables de
runtime del servicio, nunca como build args ni variables frontend.
El archivo ya fue generado el 18 de octubre; conserva el dominio pendiente
y la confirmacion de persistencia en 0. Los chequeos locales de preparacion
comprobaron la preservacion de credenciales y la adaptacion de la CA sin
conectarse a PostgreSQL. No repetir el preparador para sobreescribirlo.

| Variable / ajuste | Preparacion |
| --- | --- |
| SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY | Del proyecto existente; solo la clave publicable puede llegar al navegador |
| VIAL_DATABASE_URL | Rol vial_backend, verify-full y CA del contenedor; secreto de runtime |
| VIAL_API_STORAGE / VIAL_BACKUP_DIR | /data/archives y /data/backups |
| RAILWAY_RUN_UID | 0 para preparar volumen y bajar a uid/gid 10001 |
| RAILWAY_VOLUME_MOUNT_PATH | Lo inyecta Railway; no falsearlo manualmente |
| VIAL_PERSISTENT_STORAGE_CONFIRMED | 0 hasta validar persistencia y respaldo |
| WEB_CONCURRENCY | 1 |
| VIAL_PUBLIC_ORIGIN | Pendiente del dominio HTTPS real; no inventar hostname |
| FORWARDED_ALLOW_IPS | 127.0.0.1 por ahora; resolver proxies antes del despliegue |

Al asignar el dominio, usar el mismo origen exacto en VIAL_PUBLIC_ORIGIN y
Supabase Auth Site URL; permitir su URL raiz exacta con la barra final en las
redirect URLs. No agregar comodines de Railway. La aplicacion actual usa
email/password y confirmacion de correo; no tiene una ruta OAuth /auth/callback.
La confirmacion vuelve al sitio y el usuario inicia sesion desde alli.
Mantener confirmacion de correo, deshabilitar usuarios anonimos y, para
este piloto de dos cuentas, deshabilitar nuevos registros. No aplicar esos
cambios al proyecto hasta revisar el dominio y el alcance real.

Referencia: [URLs de Auth](https://supabase.com/docs/guides/auth/redirect-urls).

## Pendientes para cerrar preparativos

- Hobby US$5 confirmado por el usuario; falta revisar consumo y configurar alertas.
- No existe destino externo: bucket privado propuesto en OPERACION.md, sin crear cuenta.
- Subir la seleccion revisada a GitHub cuando corresponda; todavia no se hizo push.
- Recursos Railway pendientes de validaciones y revision del consumo previsto.
- Dominio real, ajustes de proxy y URLs Auth dependen del servicio futuro.
- Backup externo y recuperacion: procedimiento en OPERACION.md, sin calendario activo.
- Despues: construir imagen, verificar TLS, arranque, persistencia y restauracion.
