# Persistencia central y cuentas Supabase

Fecha inicial: **2026-10-10**. Actualizacion: **2026-10-16**.
Evidencias EV-14/EV-15/EV-16. E3-05/E3-06 verificadas; E3-07/E3-10 parciales.
Decision: Supabase Auth y PostgreSQL/PostGIS; conservar FastAPI para procesamiento.
Railway sigue como alojamiento futuro, sin desplegar ni contratar en este avance.

## Implementado

| Modulo | Responsabilidad |
|---|---|
| src/auth.py | Validar JWT con claves publicas del emisor Supabase configurado. |
| src/database.py | Modelo relacional, consultas por propietario y transacciones de trabajos/resultados. |
| src/central_api.py | Endpoints privados con autenticacion, historial, carga, resultado, mapa y ZIP original. |
| migrations/versions/0001_central.py | Revision congelada del esquema privado, geometria PostGIS e indice espacial. |
| migrations/versions/0002_backend_role.py | Rol backend sin BYPASSRLS, permisos limitados y politicas exclusivas del servidor. |
| run_migrations.py | Upgrade explicito; no modifica la base al iniciar la API. |
| run_api.py --central | Arranque que exige configuracion completa; no cae al modo anonimo. |
| web/ | Cliente con Supabase Auth, carga, historial, resultados y mapa privados. |
| run_server.py, Dockerfile, deploy/ | Preparacion del despliegue HTTPS, sin publicar un servicio. |

No se implementa un sistema propio de contrasenas. Registro, login, renovacion
y cierre de sesion usan Supabase Auth desde el cliente web. Hay dos cuentas
reales confirmadas y el flujo completo esta probado; la APK sigue sin conectar.
La recuperacion de contrasena desde la UI queda para un incremento posterior.

## Modelo de datos

- vial.users: UUID externo e issuer; no guarda contrasenas, tokens ni email.
- vial.trips: sesion importada, propietario, ID de captura, perfil y calidad.
- vial.jobs: carga, SHA-256, tiempos/estado, error y resultado JSONB; referencia
  la sesion importada al completar. Cargas iguales aun crean trabajos distintos.
- vial.observations: eventos candidatos por sesion/propietario, tipo, coordenadas
  y revision PENDING/CONFIRMED/REJECTED. No se crean automaticamente de las marcas.

FK compuestas (trip_id, owner_id) impiden asociar un trabajo/observacion de B a
una sesion de A. Se validan rango de coordenadas y estados. El punto geom se
genera desde longitud/latitud en EPSG:4326 y tiene indice GiST. Es geometry en
grados; futuras consultas de distancia en metros deben usar proyeccion adecuada
o geography, no interpretar grados como metros.

ZIP permanece en almacenamiento privado del servidor. Se prepararon volumen,
cuotas, respaldo y retencion para Railway, sin crear un servicio o volumen ni
integrar Supabase Storage. Ver [preparacion de despliegue](../../deploy/README.md).

## Seguridad y limites

La API exige Authorization: Bearer con token de acceso del usuario. Verifica
firma ES256/RS256, issuer exacto, audience authenticated, exp/iat/sub y UUID;
rechaza service_role, usuarios anonimos y HMAC/HS256. Configurar claves asimetricas
en el proyecto Supabase. No acepta URLs de claves indicadas por el token ni
contrasenas; usa exclusivamente el JWKS del proyecto configurado.
El margen temporal es 90 s, configurable entre 0 y 120, por un desfase real de
67 s detectado en Windows. Afecta las validaciones temporales estandar de
PyJWT, incluida expiracion. Sincronizar relojes antes de desplegar.

JWKS se almacena temporalmente hasta 300 s y hay timeout de 5 s. Un fallo de red
produce 503, nunca acceso anonimo. La validacion local no consulta en cada
peticion si una sesion/usuario fue revocado: un JWT valido puede seguir aceptado
hasta vencer, y la rotacion de claves esta sujeta a cache. Valorar verificacion
de sesion/revocacion segun los requisitos de la entrega y antes de produccion.

Todas las consultas privadas incluyen el propietario obtenido del token, no un
owner_id que el cliente pueda elegir. Datos ajenos devuelven 404 igual que un ID
inexistente. No poner tokens en URL, logs, archivos versionados o la APK como
credenciales de servidor.
Respuestas centrales usan Cache-Control private/no-store y Referrer-Policy
no-referrer; esto no oculta al proveedor de teselas el area solicitada.

La migracion habilita RLS y revoca PUBLIC en las cuatro tablas. Si encuentra
auth.uid(), prepara politicas SELECT por propietario para authenticated; no
concede acceso anonimo ni escritura directa de clientes. Mantener vial fuera
de los esquemas expuestos por la Data API mientras no se disene ese acceso.
No hay endpoints publicos de trayectorias u observaciones en este incremento.

Una conexion backend propietaria/BYPASSRLS no queda limitada por estas politicas:
los controles de FastAPI son obligatorios y estan probados. Migraciones necesitan
privilegios DDL/extension; el rol de ejecucion debe tener permisos coherentes con
RLS y acceso a tablas. Definir un rol backend con privilegios minimos y probarlo
en la instancia real antes del despliegue; no asumir que cualquier rol insertara
cuando RLS esta habilitado. No distribuir su DSN ni service_role a Android/web.

El procesamiento sigue con un trabajador y un proceso. Al reiniciar, estados
QUEUED/PROCESSING pasan a FAILED/PROCESS_INTERRUPTED. La base conserva resultados,
pero no hay cola durable, reintento automatico ni idempotencia. No ejecutar varios
trabajadores contra este esquema de recuperacion ni publicar la demo local sin
cuentas. Hay limites de cuerpo HTTP, concurrencia, tiempo, cuotas por cuenta y
espacio local. Falta validar capacidad en alojamiento con ZIP maximo y cargas
simultaneas; ver [EV-16](VALIDACION_CUENTAS_CLIENTE.md).

## Endpoints centrales

GET /health es publico y no contiene identidad ni secretos. Los siguientes
requieren token y solo muestran informacion del propietario:

| Ruta | Uso |
|---|---|
| GET /v1/me | UUID autenticado. |
| POST /v1/jobs | ZIP multipart, respuesta 202 con job_id. |
| GET /v1/jobs?limit=20&offset=0 | Historial privado paginado; maximo 100 por pagina. |
| GET /v1/jobs/{id} | Estado y error controlado. |
| GET /v1/jobs/{id}/result | Inspeccion disponible al completar; 409 si no. |
| GET /v1/jobs/{id}/map | HTML del trayecto privado. |
| GET /v1/jobs/{id}/archive | Descarga del ZIP original propio. |

El resultado incorpora processing_policy. Sigue siendo inspeccion, tambien
para legado; no activa RF ni deteccion nativa. El mapa protegido requiere fetch
con Authorization y mostrar el HTML recibido; abrir la URL sin token da 401.
No resolverlo colocando el token en query string. La cartografia externa puede
revelar el area a su proveedor, aunque el endpoint sea privado.

## Conexion real verificada el 16 de octubre

Proyecto **monitoreo-vial**, referencia `eqrkaypxpvjwenlclyab`, region
`us-west-2`, PostgreSQL 17.11. Se aplicaron las revisiones locales mediante el
conector Supabase sobre la instancia vacia. El SQL de la primera se genero con
las operaciones Alembic de `0001_central`, tras comprobar que no habia PostGIS
previo y que existia `auth.uid()`. El historial Supabase registra
`central_from_alembic_0001` y `backend_role_from_alembic_0002`;
`public.alembic_version` queda en `0002_backend_role`, igual al head local.
No volver a aplicar el SQL inicial sobre estas tablas.

Estan creadas las cuatro tablas `vial`, PostGIS 3.3.7 en `gis`, el punto generado
EPSG:4326 y el indice GiST. RLS esta habilitado. `anon`, `authenticated` y
`service_role` no tienen USAGE sobre `vial` ni permisos sobre sus tablas. La
aplicacion conserva el acceso privado por FastAPI; no se habilito un esquema
nuevo en la Data API.

`vial_backend` tiene LOGIN, sin SUPERUSER, CREATEDB, CREATEROLE, REPLICATION ni
BYPASSRLS. Puede leer las cuatro tablas, insertar usuarios/sesiones/trabajos y
actualizar unicamente `trip_id`, `status`, `updated_at`, `error` y `result` de
trabajos. No puede borrar trabajos, reasignar propietarios, insertar
observaciones, crear tablas ni leer `auth.users` o el historial Alembic.
Sus politicas permiten las operaciones del servidor sobre varios propietarios:
el aislamiento de cada peticion sigue siendo responsabilidad de FastAPI.
La revision crea el rol inicialmente NOLOGIN; la credencial aleatoria se
provisiono por separado. No se guarda una contrasena en codigo versionado.

La configuracion real esta en `.env`, ignorado por Git, y usa el pooler de
sesion `aws-1-us-west-2.pooler.supabase.com:5432`, usuario
`vial_backend.eqrkaypxpvjwenlclyab` y `sslmode=verify-full`. La CA publica esta
en `.api_local/supabase/prod-ca-2021.crt`, obtenida del enlace publicado en la
[configuracion oficial del panel](https://github.com/supabase/supabase/blob/master/apps/studio/hooks/custom-content/custom-content.json).
SHA-256 DER de la CA:
`807025ad50d4ed219d2c9c7d299c004f824eb00cf7f65afef607d07b72e6cafa`.
La conexion directa `db.<ref>.supabase.co` no resolvio desde este equipo.

Se verifico TLS del cliente al pooler, incluida la validacion del certificado y
del hostname. `pg_stat_ssl` informo `ssl=false` en el tramo pooler a PostgreSQL;
esto es un limite de la comprobacion y queda pendiente revisar SSL enforcement
antes del despliegue. No se desactivo la verificacion para lograr la conexion.

Auth publica una clave EC/ES256. El registro por email esta habilitado,
`mailer_autoconfirm=false` y los usuarios anonimos estan deshabilitados.
En el corte EV-15 habia cero cuentas Auth. En EV-16 se registraron las dos
direcciones solicitadas y Pablo confirmo ambos correos. Se probaron login,
renovacion, cierre y aislamiento real, conservando un trabajo por cuenta y
un trabajo adicional cargado desde el navegador en la primera.

## Configuracion y siguientes pasos

1. Proyecto, clave asimetrica y dos cuentas confirmadas ya verificados. Mantener
   la confirmacion de correo; no volver a registrar las cuentas de prueba.
2. SUPABASE_URL y VIAL_DATABASE_URL ya estan configurados localmente segun .env.example.
   El DSN debe usar TLS con verificacion de certificado; obtener los parametros
   y certificado del proyecto. La clave publica JWKS basta para validar tokens;
   el backend no necesita una clave secreta Supabase para este verificador.
3. La base actual ya esta migrada. Para futuras revisiones, configurar
   VIAL_MIGRATION_DATABASE_URL en un `.env.migrations` privado con una conexion
   administrativa autorizada. El rol runtime no tiene DDL ni acceso al historial.
   El lanzador de migraciones prioriza esa variable; conserva VIAL_DATABASE_URL
   como alternativa para configuraciones anteriores. `.env` y `.env.*` estan ignorados.
4. El flujo local de dos cuentas esta probado. Para HTTPS, seguir deploy/README.md:
   conectar Railway, verificar TLS upstream, volumen y restauracion antes de publicar.

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements-api.txt
npm.cmd --prefix web ci --ignore-scripts
npm.cmd --prefix web run build
# Solo para futuras migraciones, con conexion administrativa configurada:
.\.venv\Scripts\python.exe run_migrations.py --env-file .env.migrations
.\.venv\Scripts\python.exe run_api.py --central --env-file .env --port 8001
```

El modo central se comprobo con TestClient y con servidor real en
`http://127.0.0.1:8001`. El cliente web queda en esa misma URL mientras el
proceso este activo. El lanzador local sigue limitado a 127.0.0.1. El despliegue
HTTPS y la subida desde otro dispositivo requieren completar la preparacion.

## Pruebas realizadas y pendientes

Resultado historico: **87 passed, 1 skipped, 1 warning in 6.72s**, suite del 10/10.
Esas pruebas usaban las siguientes condiciones:

- Tokens firmados con clave EC efimera de prueba, no cuentas Supabase reales.
- Dos identidades aisladas en listado, estado, resultado, mapa y archivo.
- Persistencia/reinicio y FK/rangos comprobados sobre SQLite de pruebas.
  SQLite se rechaza en configuracion central normal: no sustituye PostGIS.
- Revision SQL congelada compila tipos/relaciones PostgreSQL y prepara RLS/GiST.
  La compilacion y los dobles de operacion no prueban ejecucion DDL real.
- Prueba optativa tests/test_postgis_live.py omitida porque falta instancia.
  Con VIAL_TEST_DATABASE_URL de una base descartable aplica upgrade, inserta
  datos sinteticos, consulta el punto EPSG:4326 y comprueba RLS. No apuntar esa
  variable a datos de produccion: la prueba modifica el esquema y deja fixtures.
- Advertencia restante: deprecacion de httpx en Starlette TestClient, sin fallo.

Comprobaciones nuevas del **16/10**:

- Suite local: **87 passed, 8 skipped**. Las omisiones son la prueba descartable
  PostGIS y siete comprobaciones runtime optativas; no se ejecutan contra una
  instancia remota sin configurar su variable especifica.
- `tests/test_backend_postgres_live.py`: **7 passed in 49.90s** con el DSN real de
  `vial_backend`. Verifica creacion, procesamiento, resultado JSONB, fallo y
  consultas por propietario; seis casos comprueban permisos rechazados con
  SQLSTATE 42501. Cada prueba revierte su transaccion, sin cuentas Auth ni
  registros sinteticos persistentes. Se observo una advertencia local de acceso
  a la cache de pytest; no fue un fallo de permisos PostgreSQL.
- Comprobacion administrativa dentro de BEGIN/ROLLBACK: geometria generada con
  SRID 4326, X=longitud, Y=latitud; FK compuesta rechaza propietario ajeno y CHECK
  rechaza latitud 100. No se apunto VIAL_TEST_DATABASE_URL a esta instancia.
- Arranque real del modo central: `/health` devuelve 200; `/v1/me` y `/v1/jobs`
  sin token devuelven 401; token malformado tambien devuelve 401.
- Asesor de seguridad: sin ERROR/WARN. Un aviso INFO indica que
  `public.alembic_version` tiene RLS sin politicas. Es intencional: clientes y
  runtime no tienen acceso al historial, que solo usa el administrador.
  [Detalle del aviso](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

Para repetir solo las pruebas runtime, sin ejecutar migraciones, usar:

```powershell
@'
from dotenv import load_dotenv
import os, pytest
load_dotenv('.env', override=False)
os.environ['VIAL_RUNTIME_TEST_DATABASE_URL'] = os.environ['VIAL_DATABASE_URL']
raise SystemExit(pytest.main(['-q', '-p', 'no:cacheprovider', 'tests/test_backend_postgres_live.py']))
'@ | .\.venv\Scripts\python.exe -
```

## Avance EV-16: cuentas y cliente completos

Ver [validacion integrada](VALIDACION_CUENTAS_CLIENTE.md): dos cuentas reales,
dos ZIP completados, mapa/resultado/original propio, ocho accesos cruzados 404,
renovacion y cierre verificados. Cliente probado en Edge, tokens solo en memoria.
Suite Python: 106 aprobadas, ocho omisiones optativas. Cliente JS: siete aprobadas.
Respaldo privado de aplicacion y originales verificado; retencion simulada sin borrar.

El asesor actual muestra WARN por proteccion contra contrasenas filtradas
deshabilitada; el plan Free no incluye esa funcion. Ver
[la limitacion y su referencia](../../deploy/README.md#requisitos-externos-pendientes).
Se conserva el INFO esperado del historial Alembic sin politicas.

Pendientes: publicacion HTTPS (conexion Railway, TLS upstream, respaldo externo
y ejercicio de restauracion), idempotencia/cola durable, observaciones
revisadas/publicacion, filtros geograficos y subida APK, pospuesta por Pablo.

## Referencias

[Claves y JWKS Supabase](https://supabase.com/docs/guides/auth/signing-keys),
[Auth](https://supabase.com/docs/guides/auth),
[RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[PostGIS](https://supabase.com/docs/guides/database/extensions/postgis),
[PyJWT](https://pyjwt.readthedocs.io/en/stable/usage.html),
[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
