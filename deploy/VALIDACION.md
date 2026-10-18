# Validacion para despliegue

Fecha: 2026-10-18. No hay publicacion en Railway ni cambios del plan Hobby.

## Evidencia local

| Comprobacion | Resultado |
| --- | --- |
| Python: .venv/Scripts/python.exe run_tests.py | 106 aprobadas, 8 omitidas; 1 aviso de deprecacion TestClient/httpx |
| Cliente: npm --prefix web test | 7 aprobadas |
| Cliente: npm --prefix web run build | Aprobado; el sandbox requirio ejecutar esbuild con acceso a carpetas padre |
| Paquete de fuente y patrones de secretos | Preparado sin variables privadas; los ZIP RAW se conservan fuera del indice |
| Acceso a GitHub | Repositorio publico, permisos de escritura y push dry-run comprobados |

Las pruebas omitidas no acreditan PostgreSQL/PostGIS real ni todo el piloto
opcional. No se ejecutaron las migraciones de pruebas contra la base activa.
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
| TLS pooler a PostgreSQL, pg_stat_ssl | false; bloquea produccion |
| Acceso a jobs y geom de observations | Correcto, sin leer datos de usuarios |

El usuario indico que activara Enforce SSL en el dashboard y avisara.
No se considera aplicado hasta su aviso y una reconexion que compruebe ssl=true.
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

Ejecucion remota pendiente de registrar al terminar GitHub Actions.
Las ejecuciones con runner estandar del repositorio publico son gratuitas
segun [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
No se usan larger runners, artefactos persistentes ni caches remotos.

Esta comprobacion no ejecuta el entrypoint de produccion ni acredita TLS,
autenticacion con cuentas reales, persistencia o restauracion del servicio final.

## Pendientes antes de publicar

- Confirmar TLS pooler/PostgreSQL despues del cambio del usuario.
- Registrar resultado del build y arranque sintetico en Linux.
- Restauracion descartable de PostgreSQL/Auth y originales desde copia externa.
- Prueba del maximo de 64 MiB y concurrencia en el alojamiento.
- Configurar volumen, dominio HTTPS, proxies y URLs Auth al autorizar el servicio.
- Verificar arranque real, cuentas, aislamiento y persistencia despues de reiniciar.
- Confirmar costo, alertas y limite de uso dentro de Hobby antes de crear recursos.
