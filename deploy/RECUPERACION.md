# Recuperacion de aplicacion: incremento del 18 de octubre de 2026

## Implementacion y limites

`scripts/restore_application.py` inspecciona el formato `vial-backup-1` y puede
restaurar las cuatro tablas `vial` y originales hacia una base descartable
ya migrada. La linea de comandos no carga `.env`, no usa VIAL_DATABASE_URL
y no aplica migraciones automaticamente. La inspeccion es el modo por defecto.

Antes de escribir comprueba version, columnas, conteos, UUID, fechas con zona,
estados terminales, originales completos, tamanos y SHA-256. Rechaza archivos
extra, rutas ajenas al formato, entradas duplicadas y enlaces simbolicos.
Los limites iniciales son 64 MiB por original, 64 MiB por JSON y 4 GiB
descomprimidos en total. No importa `geom`: PostgreSQL la calcula.

La aplicacion se detiene durante la operacion. El destino debe tener las cuatro
tablas vacias y el directorio debe ser nuevo. En PostgreSQL solo acepta nombres
de base `vial_restore_*`; bloquea el nombre `postgres` del proyecto activo.
Esta restriccion hace que sea una herramienta de ensayo descartable, no un
restaurador general sobre un proyecto Supabase. El comando requiere una
conexion administrativa independiente para insertar las observaciones.
El rol del servidor habitual sigue limitado y no recibe privilegios nuevos.

Las filas se insertan en una transaccion. Si falla una FK o cualquier insercion,
se revierten y se retiran solo los archivos/directorios creados por esa llamada.
No se borran arboles preexistentes ni se usa extractall. Esto no promete una
transaccion atomica entre disco y PostgreSQL frente a un corte del proceso o
energia; un destino interrumpido debe inspeccionarse antes de reutilizarse.

## Evidencia local, sin modificar produccion

- Suite local tras implementar el restaurador: 120 aprobadas, 8 omitidas.
- Pruebas de restauracion: 15 casos cubren la copia correcta, preservacion de
  UUID/fechas/JSON, hash/tamano alterados, originales faltantes, trabajos activos,
  conteos, geom no admitida, fechas sin zona, rutas inseguras, entradas duplicadas,
  destinos existentes, rollback tras una FK invalida y rechazo del nombre de
  base activo antes de conectarse.
- Copia aislada del respaldo local existente: 2 usuarios internos de vial,
  3 recorridos, 3 trabajos y 3 originales recuperados, con hashes verificados.
  La base de destino de ese ensayo fue SQLite, explicitamente habilitada solo
  como backend de prueba. No acredita PostgreSQL, PostGIS ni Supabase Auth.
- El informe y la copia recuperada quedan en `.api_local/recovery-local/`,
  fuera de Git y del contexto Docker. No se enviaron datos privados a CI.

El respaldo existente no se genero en esta ejecucion: no se detuvo ni se
modifico la base activa. No se borraron los originales de la aplicacion.

## Ensayo PostgreSQL/PostGIS preparado, pendiente de ejecutar

El workflow `Validate container` agrega un job `recovery` con dos contenedores
PostgreSQL 17/PostGIS 3.6 descartables, uno de fuente y otro de destino. Los
roles son globales al cluster: usar dos servidores evita que el rol creado
por la primera migracion interfiera con la segunda.

El job instala dependencias exactas con hashes (`requirements-server.lock` y
`requirements-maintenance.lock`), aplica las migraciones en ambos servidores,
genera dos propietarios/recorridos/trabajos/observaciones sinteticos, exporta
el snapshot y lo restaura. Comprueba igualdad de UUID, fechas y JSON, geometria
generada y SRID 4326, hashes, aislamiento de propietarios y lectura tras cerrar
y volver a crear conexiones con el rol backend restringido.

No usa conexiones ni credenciales Supabase, no crea proyectos Railway, no
publica imagenes, no carga backups privados como artefactos y no certifica
persistencia de un volumen Railway. Los passwords del YAML son fixtures
efimeras de estos servicios locales, no secretos de produccion.
Todavia no hay una ejecucion que acredite este job nuevo. La aprobacion del
primer build Docker sigue referida al codigo anterior; este incremento
necesita otra construccion y el nuevo ensayo.

Referencia: [servicios PostgreSQL en GitHub Actions](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers)
y [imagen PostGIS](https://github.com/postgis/docker-postgis).

## Uso del restaurador, solo sobre destinos descartables

Desde la raiz, inspeccionar sin conectarse a una base:

```text
python -m scripts.restore_application RUTA_PRIVADA_AL_SNAPSHOT.zip
```

Para aplicar, aprovisionar por separado la base vacia `vial_restore_*`, aplicar
las revisiones y definir VIAL_RESTORE_DATABASE_URL de manera privada. El padre
del directorio destino debe existir; el directorio mismo no debe existir.

```text
python -m scripts.restore_application RUTA_PRIVADA_AL_SNAPSHOT.zip --target DIRECTORIO_NUEVO --apply --confirm-disposable
```

No poner un DSN real ni claves en comandos del chat, argumentos de build o Git.
El CLI informa el tipo de error sin imprimir excepciones que puedan contener
la conexion. La API y todos los procesos que escriban deben estar detenidos.

## Cobertura que falta

El snapshot no contiene Auth, sesiones, roles ni una copia completa de
PostgreSQL. El ensayo sintetico comprueba propietarios de vial; no autentica
cuentas recuperadas de Supabase. No acredita respaldo externo, cifrado,
retencion remota, recuperacion de Auth ni RPO/RTO del servicio completo.
El destino externo aun no fue creado ni se contrataron recursos.

El restaurador exige cero originales faltantes. Un snapshot posterior a borrar
originales vencidos no satisface ese requisito; antes de activar retencion
automatica hay que definir como recuperar historiales con originales expirados.
La eliminacion automatica sigue deshabilitada.
