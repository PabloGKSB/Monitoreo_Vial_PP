# Cuentas reales, cliente web y preparacion de despliegue

Fecha: **2026-10-16**, America/Santiago. Evidencia **EV-16**.

## Alcance comprobado

Se registraron dos cuentas solicitadas por Pablo (Gmail e institucional), con
contrasenas aleatorias guardadas unicamente en
`.api_local/supabase/auth-test.private.json`, excluido de Git. Pablo confirmo
ambos correos. Se verificaron dos usuarios con `email_confirmed_at` en Auth y
dos UUID diferentes al iniciar sesion. No se deshabilito la confirmacion.

El cliente de `web/` se sirve en la raiz de la API central. No sustituye la
interfaz Streamlit experimental. Permite registro, login, renovacion automatica,
cierre de sesion, carga de ZIP, historial paginado, resultado, mapa y descarga
del original. Usa Supabase JS **2.118.0**, Leaflet **1.9.4** y esbuild **0.28.2**,
con versiones exactas y `package-lock.json`. Las dependencias se empaquetan
localmente; no se cargan scripts desde CDN.

Los tokens viven solo en memoria del SDK (`persistSession: false`), no en URL,
localStorage ni sessionStorage. Cerrar o recargar la pagina requiere volver a
iniciar sesion. Cada solicitud lleva Authorization Bearer. Ante 401, el cliente
renueva una vez y reintenta; no reintenta cargas ante errores de red, para no
crear trabajos duplicados. Cambiar de cuenta cancela las solicitudes anteriores
y limpia resultados, historial y mapa. El cierre usa `scope: local`, revoca la
sesion del navegador y limpia la vista aunque falle la confirmacion remota.

El endpoint publico `/v1/client-config` solo entrega URL del proyecto, clave
`sb_publishable_` y limite de carga. Rechaza claves secretas/service_role. No
entrega el DSN, contrasenas o configuracion administrativa. Los recursos del
cliente llevan CSP y las respuestas mantienen private/no-store y no-referrer.
El mapa recibe GeoJSON protegido y muestra discontinuidades como partes
separadas. OpenStreetMap recibe las solicitudes de teselas del area mostrada.

## Desfase de reloj encontrado

La primera prueba con un token real fallo con `ImmatureSignatureError`: el
reloj de Windows estaba aproximadamente **67 segundos atrasado** frente al
emisor. Se agrego `VIAL_JWT_LEEWAY_SECONDS=90`, configurable entre 0 y 120.
Se usa el margen estandar de PyJWT en la validacion temporal, incluidos exp,
iat y nbf. Los tokens fuera del margen siguen rechazados. No se cambio el
reloj del sistema ni se deshabilito firma, issuer, audience o expiracion.
Sincronizar relojes en produccion; el margen no sustituye esa tarea.

La revocacion de refresh tokens se comprobo al cerrar sesiones. El verificador
local de JWT aun puede aceptar un access token emitido previamente hasta su
expiracion, considerando el margen temporal. No consulta `auth.sessions` en
cada peticion y no promete revocacion instantanea de access tokens.

Correccion posterior del 16/10: se reviso un aviso de confirmacion mostrado al
entrar. Ambos correos seguian confirmados y ambos logins reales aprobaron.
El cliente usaba un mensaje generico que sugeria confirmar correo incluso ante
credenciales invalidas; ahora distingue `invalid_credentials` de
`email_not_confirmed`, limites de intentos y fallos de servicio. Se comprobo
la distincion en Edge con respuestas controladas mediante
`scripts/check_login_feedback.py`, sin enviar nuevos correos. La anotacion de
estado del archivo privado de pruebas tambien quedo actualizada a confirmed.

## Prueba integrada real

Entrada: captura nativa del 28/09, **17.497.742 bytes**, sin modificar RAW.
SHA-256:
`be762e8966e00b0d6417adc0e0186cf1ee98fb87ab988cce2e8295623e914868`.

| Comprobacion | Cuenta A | Cuenta B |
|---|---|---|
| Login y `/v1/me` con identidad correcta | Aprobada | Aprobada |
| ZIP aceptado y trabajo COMPLETED | Aprobada | Aprobada |
| Resultado capture-preview-2, modo inspeccion | Aprobada | Aprobada |
| Mapa protegido disponible | Aprobada | Aprobada |
| ZIP descargado conserva SHA-256 | Aprobada | Aprobada |
| Historial contiene el trabajo propio | Aprobada | Aprobada |
| Renovacion conserva identidad | Aprobada | Aprobada |
| Cierre impide renovar el refresh token | Aprobada | Aprobada |

Se hicieron ocho consultas cruzadas (estado, resultado, mapa y archivo en
ambas direcciones): todas devolvieron **404**. Los historiales excluyeron el
trabajo ajeno. El historial sin token devolvio 401.

Cada cuenta conserva un trabajo real de validacion y su ZIP, para revision
manual. Ademas, la cuenta A cargo el mismo ZIP desde el navegador como
`validacion-navegador.zip`, comprobando el formulario completo. A diferencia de
las pruebas rollback de EV-15, estos trabajos no se eliminaron. Hay dos usuarios
de aplicacion, tres sesiones importadas, tres trabajos y cero observaciones:
las marcas no se convierten automaticamente en defectos confirmados.

La comprobacion completa tardo **59,91 s**; cada flujo de carga a verificaciones
de resultado/archivo tardo **21,84 s** y **21,80 s**. Incluye latencia de
consultas remotas; no es una medicion aislada del algoritmo. PeakWorkingSet64
de Windows para el proceso API: **248.320.000 bytes**, aproximadamente
**236,8 MiB**. No acredita el maximo permitido de 64 MiB ni cargas paralelas.

Artefactos privados: `.api_local/supabase/e2e-report.json`,
`resource-measurement.json` y `browser/report.json`.

## Navegador y pruebas automatizadas

Edge headless, pantalla 1365x1000 y revision del login a 390 px:

- Ambas cuentas entran, ven su historial, muestran cuatro indicadores y mapa,
  descargan el original y cierran sesion.
- El formulario de carga del navegador tambien acepta y completa el ZIP real
  de 17,5 MB; el trabajo adicional queda en la primera cuenta.
- Se simulo un 401 inicial para comprobar renovacion real con Supabase y
  reintento exitoso del navegador.
- No hubo errores JavaScript; no se guardaron tokens en almacenamiento web.
- Capturas privadas en `.api_local/supabase/browser/`; no se versionan emails
  ni trayectorias mostradas.

Suite Python: **106 passed, 8 skipped**. Las omisiones corresponden a pruebas
remotas optativas; una advertencia conocida de Starlette/httpx permanece.
Cliente JavaScript: **7 pruebas aprobadas**. Compilacion del cliente aprobada.
Docker no esta instalado en este equipo: **no se construyo ni ejecuto la imagen**.

## Limites de carga y almacenamiento

- ZIP: maximo 64 MiB; cuerpo HTTP: 66 MiB, con espacio para multipart.
- El guard recibe el cuerpo de forma acotada antes de parsear multipart, limita
  cargas simultaneas a cuatro y el tiempo de recepcion a 60 s.
- Cuotas por propietario: 20 trabajos y 256 MiB en una ventana movil de 24 h,
  configurables. Consulta por propietario/fecha con el indice existente; un
  advisory lock transaccional serializa comprobacion e insercion por usuario.
- Antes de guardar un ZIP se exige espacio para las cuatro cargas maximas mas
  una reserva de 256 MiB; insuficiencia devuelve 507. Son limites de demo,
  sin cola durable ni capacidad productiva certificada.
- `scripts.retain_archives` propone originales finalizados de mas de 30 dias,
  sin seguir enlaces. Por defecto solo simula; `--delete-expired` elimina
  exclusivamente `input.zip`, conservando resultados/historial. No se programo
  un borrado automatico ni se elimino un original real.
- `scripts.backup_central` crea un snapshot consistente de las cuatro tablas
  y sus originales, con CRC y SHA-256. Se genero un respaldo privado local con
  tres originales y cero faltantes en `.api_local/backups/`. Excluye Auth y
  credenciales; no equivale a un respaldo completo de Supabase o uno externo.

## Repeticion

```powershell
npm.cmd --prefix web ci --ignore-scripts
npm.cmd --prefix web run build
.\.venv\Scripts\python.exe run_api.py --central --env-file .env --port 8001
# En otra terminal; crea un trabajo adicional por cuenta:
.\.venv\Scripts\python.exe scripts/validate_accounts.py --zip 'Data/raw/test_20260928_140148_062_anotaciones_imu_1790636845152.zip'
.\.venv\Scripts\python.exe scripts/check_web_client.py
# Opcional: agrega un trabajo para comprobar tambien el formulario de carga:
# .\.venv\Scripts\python.exe scripts/check_web_client.py --upload-zip 'Data/raw/test_20260928_140148_062_anotaciones_imu_1790636845152.zip'
.\.venv\Scripts\python.exe -m scripts.retain_archives --days 30
.\.venv\Scripts\python.exe -m scripts.backup_central
```

La prueba de navegador requiere Playwright y Edge; es una dependencia de QA,
excluida del servidor. No volver a ejecutar el registro de cuentas ya creadas.

## Siguiente paso

La preparacion tecnica de HTTPS, volumen, respaldo y restricciones de arranque
esta en [la guia de despliegue](../../deploy/README.md). Railway aun no esta
conectado y no se creo, contrato ni publico un servicio. TLS del tramo
pooler-PostgreSQL sigue pendiente de activar/verificar. La subida APK se
pospuso por indicacion de Pablo, hasta revisar estos resultados.
