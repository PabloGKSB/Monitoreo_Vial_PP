# Validacion para despliegue

Fecha: 2026-10-18. No hay publicacion en Railway ni cambios del plan Hobby.

## Evidencia local

| Comprobacion | Resultado |
| --- | --- |
| Python: .venv/Scripts/python.exe run_tests.py | 106 aprobadas, 8 omitidas; 1 aviso de deprecacion TestClient/httpx |
| Cliente: npm --prefix web test | 7 aprobadas |
| Cliente: npm --prefix web run build | Aprobado; el sandbox requirio ejecutar esbuild con acceso a carpetas padre |
| Backend PostgreSQL real: tests/test_backend_postgres_live.py | 7 aprobadas en 38,90 s; transacciones revertidas, sin migraciones ni altas Auth |
| Paquete de fuente y patrones de secretos | Preparado sin variables privadas; los ZIP RAW se conservan fuera del indice |
| Acceso a GitHub | Repositorio publico, permisos de escritura y push dry-run comprobados |

De las ocho omisiones iniciales, las siete de backend se ejecutaron despues
con el DSN optativo del rol limitado y aprobaron. La prueba de migraciones
PostGIS sigue pendiente de una base descartable; no se ejecutaron las
migraciones de pruebas contra la base activa. Este resultado no acredita
todo el piloto opcional ni una restauracion.
El aviso de TestClient no afecto los resultados y no se cambiaron dependencias.

## Base real, solo lectura

Comando: `.venv/Scripts/python.exe -m scripts.check_deployment_database`.
Usa el DSN privado local, exige verify-full y no muestra credenciales ni filas.
Consultas dentro de transaccion READ ONLY, seguida de rollback.

| Comprobacion | Resultado |
| --- | --- |
| Estado del proyecto | ACTIVE_HEALTHY; region us-west-2 |
| Rol backend | vial_backend sin superuser, bypassrls, createrole ni createdb |
| Verificacion CA/hostname | sslmode=verify-full con CA existente |
| TLS cliente a pooler | true |
| TLS pooler a PostgreSQL, pg_stat_ssl | true, confirmado tras el cambio del usuario |
| Acceso a jobs y geom de observations | Correcto, sin leer datos de usuarios |

El usuario activo Enforce SSL en el dashboard y aviso. Se reconecto con el
rol backend y la comprobacion devolvio `ready=true`: ambos tramos TLS,
verify-full, rol limitado y esquema accesible. Ese resultado corresponde
solo a la preparacion de la conexion, no a toda la aplicacion en produccion.
No se cambio la configuracion de la base desde estas herramientas.
Referencia: [SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement).

El asesor conserva WARN por proteccion de contrasenas filtradas deshabilitada:
[remediacion](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).
El INFO de alembic_version con RLS sin politicas es consistente con el cierre
intencional del historial a clientes/runtime:
[detalle](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

## Contenedor Linux

Workflow `Validate container`: construye linux/amd64 sin secretos y ejecuta
`scripts/check_container_image.py` dentro de la imagen, sin red, con raiz de
solo lectura y /tmp efimero escribible por uid/gid 10001.
Comprueba Python 3.12, ausencia de Node y archivos privados, cliente compilado,
CA publica y arranque de la API con SQLite sintetico: /health 200, frontend
200 y recurso privado sin token 401. La imagen no se publica en un registro.

El usuario autorizo la subida publica y la apertura del PR. Rama
`codex/validacion-despliegue`, [PR #1 en borrador](https://github.com/PabloGKSB/Monitoreo_Vial_PP/pull/1),
sin fusionar a main ni publicar en Railway.

[Ejecucion 39154037300](https://github.com/PabloGKSB/Monitoreo_Vial_PP/actions/runs/39154037300):
**success**, con todos los pasos aprobados sobre el codigo del commit
`5873396deb7682d01d6e0f84b7c9666db07a74b6` (checkout del merge temporal del PR).
El resultado del proceso dentro del contenedor fue:

```json
{"checks":{"health":200,"frontend":200,"unauthenticated":401},"uid":10001,"runtime_node":false,"backend":"isolated-synthetic-sqlite","network":"none","production_entrypoint_checked":false,"production_validated":false}
```

Plataforma `linux/amd64`. ID local de imagen en ese runner:
`sha256:8e93ded6572eec55edc7a906d86063fcf1fa3703255ab6797ee2f7fa233c6c10`.
Es el ID de esa construccion, no un digest de registro: no se publico ni
conservo la imagen fuera del runner efimero. Railway debera reconstruir
el mismo codigo y comprobarse de nuevo en el entorno final.

El commit posterior que registra esta evidencia solo cambia documentacion;
no modifica el codigo validado y omite otra ejecucion de CI.
Las ejecuciones con runner estandar del repositorio publico son gratuitas
segun [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
No se usan larger runners, artefactos persistentes ni caches remotos.

Esta comprobacion no ejecuta el entrypoint de produccion ni acredita TLS,
autenticacion con cuentas reales, persistencia o restauracion del servicio final.

## Pendientes antes de publicar

Incremento local de recuperacion: restaurador descartable, pruebas y job de
CI PostgreSQL/PostGIS preparados. Ver [RECUPERACION.md](RECUPERACION.md).
120 pruebas locales aprobaron y el respaldo local existente se recupero en
SQLite aislado, sin cambios en produccion. El job nuevo todavia no se ejecuto;
el resultado Docker anterior no valida este codigo adicional.

- Restauracion descartable de PostgreSQL/Auth y originales desde copia externa.
- Prueba del maximo de 64 MiB y concurrencia en el alojamiento.
- Configurar volumen, dominio HTTPS, proxies y URLs Auth al autorizar el servicio.
- Verificar arranque real, cuentas, aislamiento y persistencia despues de reiniciar.
- Confirmar costo, alertas y limite de uso dentro de Hobby antes de crear recursos.
