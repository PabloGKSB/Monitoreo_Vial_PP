# Preparacion de despliegue de Monitoreo Vial

Actualizado: 2026-10-18. Estado: **validacion en curso, sin publicar en Railway**.
Railway ya esta conectado: usuario `pablogksb`, workspace personal
`pablogksb's Projects`, sin proyectos accesibles en la revision del 18 de octubre.
El usuario confirma plan Hobby de US$5; el conector no permitio consultar
facturacion ni consumo. No se cambio el plan ni se generaron servicios,
dominios o volumenes durante esta preparacion.

La seleccion de fuente, entorno Docker, variables y propuesta de costos se
encuentran en [PREPARACION.md](PREPARACION.md). La politica operativa propuesta
esta en [OPERACION.md](OPERACION.md). Ninguna propuesta equivale a un recurso
provisionado, una suscripcion aprobada o una validacion completada.
El resultado actual de las comprobaciones se registra en
[VALIDACION.md](VALIDACION.md).

## Paquete disponible

- `Dockerfile`: cliente Node 22 en una etapa y Python 3.12 en otra. Runtime
  sin Node/Streamlit, con dependencias exactas y hashes en
  `requirements-server.lock`. Las dependencias del cliente tienen lockfile.
- `.dockerignore`: solo admite fuente necesaria, cliente, CA publica y
  scripts de mantenimiento. Excluye `.env`, RAW, APK, credenciales, resultados
  y respaldos locales.
- `run_server.py`: puerto `PORT`, bind 0.0.0.0, un proceso Uvicorn, sin
  migraciones al iniciar ni logs de acceso con query strings.
- Preflight: exige origen HTTPS, clave publicable, rol backend sin privilegios,
  `verify-full` con CA, TLS cliente/pooler y pooler/PostgreSQL, cliente compilado
  y almacenamiento configurado dentro de un volumen confirmado.
- Con origen publico configurado, la aplicacion exige Host correcto y HTTPS;
  el healthcheck interno puede usar HTTP. HSTS se activa en respuestas HTTPS.

No se agrego un railway.toml legado: la [documentacion vigente](https://docs.railway.com/config-as-code/reference)
indica su deprecacion para configuraciones nuevas. Railway detecta el
Dockerfile; los ajustes del servicio se registraran al conectarlo.

## Configuracion del servicio antes de publicarlo

1. Elegir el proyecto dentro del workspace Railway ya conectado. Revisar el
   costo concreto antes de contratar recursos o publicar un servicio de pago.
2. Construir la imagen en un entorno con Docker/Linux amd64. **No fue posible
   construirla localmente porque Docker no esta instalado.** Hay un workflow
   Linux preparado en `.github/workflows/build-container.yml`, manual o al
   abrir/actualizar un pull request hacia main. Incluye un arranque aislado
   sin red con datos sinteticos; no acredita la configuracion de produccion.
   La [primera construccion y prueba aislada](https://github.com/PabloGKSB/Monitoreo_Vial_PP/actions/runs/39154037300)
   aprobo el 18 de octubre; detalle en VALIDACION.md. Validar arranque
   y healthcheck con la imagen antes de exponer un dominio.
3. Adjuntar un volumen en `/data`, con capacidad medida segun uso y alertas.
   Configurar `VIAL_API_STORAGE=/data/archives` y respaldos temporales en
   `/data/backups`. Una sola replica, sin autoscaling ni despliegues simultaneos
   que procesen la misma base. El worker no es una cola distribuida.
4. Railway [monta volumenes como root](https://docs.railway.com/volumes#permissions).
   Para el arranque usar `RAILWAY_RUN_UID=0`: el lanzador solo asigna `/data`
   y `/data/archives` a uid/gid 10001, y baja sus privilegios antes de iniciar
   la API. La imagen usa uid 10001 por defecto para otros entornos.
5. Cargar las variables del ejemplo `.env.production.example` en el gestor de
   secretos del proveedor. Adaptar el DSN al contenedor: CA en
   `/app/deploy/prod-ca-2021.crt`, nunca la ruta de Windows. No pasar el DSN
   al build o al cliente web. No copiar una conexion administrativa.
6. Generar un dominio con [HTTPS de Railway](https://docs.railway.com/networking/public-networking)
   y configurar `VIAL_PUBLIC_ORIGIN` con ese origen exacto. Healthcheck `/health`.
   Autorizar solo los proxies de confianza en `FORWARDED_ALLOW_IPS`; `*` solo
   si el edge es el unico acceso al backend y sanitiza esos headers.
7. Configurar en Supabase Auth el Site URL y las redirect URLs de ese dominio.
   Mantener confirmacion de correo y usuarios anonimos deshabilitados.
8. Tras comprobar persistencia y respaldo, poner
   `VIAL_PERSISTENT_STORAGE_CONFIRMED=1`. Es una declaracion del operador,
   no una comprobacion automatica del proveedor o de su facturacion.

## Requisitos externos pendientes

**TLS upstream resuelto el 18 de octubre:** el usuario activo
[SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)
desde los ajustes del proyecto. Una conexion nueva con el rol `vial_backend`
confirmo TLS cliente/pooler y `ssl=true` en `pg_stat_ssl` para el tramo
pooler/PostgreSQL, conservando `verify-full` y la CA. La consulta fue de solo
lectura. Este requisito queda aprobado; no acredita los demas controles del
preflight ni la aceptacion completa del despliegue.

**Aviso Auth real:** el asesor devuelve WARN por proteccion contra contrasenas
filtradas deshabilitada. El plan actual es Free y esta funcion requiere
[Pro o superior](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
Las dos cuentas de prueba usan contrasenas aleatorias. No se cambio el plan ni
se habilito un costo. Registrar la decision antes de abrir registro a terceros.
El unico aviso INFO adicional corresponde a `public.alembic_version` con RLS
sin politicas: el historial esta cerrado a clientes/runtime de forma intencional.
[Detalle del INFO](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

## Operacion y durabilidad

Politica inicial propuesta: originales durante 30 dias, revision diaria de
retencion y respaldos antes de borrar; resultados e historial permanecen en
PostgreSQL. Hasta configurar la tarea, no hay eliminacion automatica. Con la
API detenida, simular antes de ejecutar el borrado:

```text
python -m scripts.retain_archives --days 30
python -m scripts.retain_archives --days 30 --delete-expired
python -m scripts.backup_central
```

El snapshot de aplicacion incluye tablas `vial` y originales; no incluye Auth,
secretos ni una copia completa de PostgreSQL. Se verificaron CRC y SHA-256 de
un respaldo local de los tres trabajos reales. Una copia en el mismo disco o
volumen no protege contra la perdida de ese volumen.

Antes de publicar, configurar y verificar un respaldo externo del volumen y
una estrategia PostgreSQL/Auth compatible con el plan. Railway ofrece
[respaldos de volumen](https://docs.railway.com/volumes/backups); revisar costo
y retencion antes de habilitarlos. No se activo un calendario remoto.

Ejercicio de restauracion pendiente: restaurar en una base y volumen
descartables, aplicar las revisiones, importar UUID/fechas/JSONB sin la columna
`geom` generada, comprobar FK/SRID y los hashes de originales, y autenticar dos
cuentas con el issuer correspondiente. No restaurar sobre datos existentes.
La validacion CRC/SHA local no acredita ese ejercicio ni un RPO/RTO.

Limites de la aplicacion: ZIP 64 MiB, HTTP 66 MiB, cuatro recepciones simultaneas,
un trabajador y 60 s de recepcion. La plantilla de produccion propone 20 trabajos
y 32 MiB por cuenta en 24 h para dos cuentas piloto y 512 MiB de reserva;
el valor predeterminado del codigo sigue en 256 MiB. Un ZIP mayor a 32 MiB
superara la cuota piloto aunque sea menor al maximo tecnico de 64 MiB.
Hay respuestas 413/429/507. No hay idempotencia,
cola durable, reintento automatico o HA. El pico observado de memoria con un
ZIP de 17,5 MB fue aproximadamente 236,8 MiB; falta medir el limite de 64 MiB y
concurrencia en el alojamiento. No se certifica capacidad productiva.

## Aceptacion tras desplegar

- `/health` HTTPS devuelve 200 y una peticion privada sin token devuelve 401.
- Login, renovacion y cierre reales desde el dominio publico.
- `scripts/validate_accounts.py --api https://DOMINIO --zip ARCHIVO.zip`
  aprueba ambas cuentas, ocho accesos cruzados y hashes de descarga.
- Reiniciar el servicio conserva historial/resultados y originales del volumen.
- Confirmar rol backend, TLS de ambos tramos, espacio, backup externo y prueba
  de restauracion. Solo despues conectar la subida Android al mismo contrato.
