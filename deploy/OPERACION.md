# Respaldo, retencion y recuperacion propuestos

Fecha: 2026-10-18. Esta es una politica preparada; no hay destino remoto,
automatizacion, credenciales de respaldo ni restauracion acreditada.
Responsable inicial: operador del piloto. Nunca enviar respaldos por el chat,
Git, artefactos de Actions ni buckets publicos: contienen recorridos y datos personales.

## Alcance y destino

Se necesitan dos coberturas: snapshot de aplicacion (tablas vial y originales)
y respaldo PostgreSQL/Auth del proveedor. `scripts/backup_central.py` solo cubre
la primera; no incluye Auth, roles, secretos ni toda la base PostgreSQL.

El usuario confirma que no tiene un destino. Propuesta: Cloudflare R2 Standard,
bucket S3 compatible privado en una cuenta distinta de Railway, con cifrado
del proveedor, acceso minimo a su prefijo, proteccion contra borrados si esta
disponible y credenciales fuera del repositorio. Cifrar los archivos
antes de subirlos; guardar la clave de recuperacion fuera de Railway y probar
que puede recuperarse. No se eligio proveedor ni se contrataron recursos.
La cuota gratuita no garantiza costo cero. Once snapshots completos de unos
2 GiB podrian ocupar aproximadamente 24 GB, porque los ZIP de originales ya
estan comprimidos y no se asume deduplicacion. Con Standard a US$0,015/GB-mes
y 10 GB-mes gratuitos, el almacenamiento adicional rondaria US$0,21/mes en
ese ejemplo, mas operaciones fuera de franquicia e impuestos. El cifrado
conserva aproximadamente ese orden de magnitud. Es una estimacion, no una
contratacion ni un presupuesto aceptado. Revisar
[tarifas R2](https://developers.cloudflare.com/r2/pricing/) al confirmar el destino.
Un NAS privado externo tambien puede servir para el piloto.

## Frecuencia y retencion propuestas

| Contenido | Frecuencia | Retencion |
| --- | --- | --- |
| Snapshot completo de aplicacion | Diario, 03:00 America/Santiago, con ventana de mantenimiento | 7 diarios y 4 semanales |
| Base PostgreSQL/Auth | Diario, segun soporte del plan; definir antes de publicar | Minimo 7 diarios; confirmar cobertura Auth y restauracion |
| Respaldo previo a migracion/borrado | Antes de cada operacion | Hasta cerrar su verificacion y recuperacion |
| Originales del volumen | Revision diaria, conservar 30 dias | Solo borrar con copia externa comprobada |
| Copia ZIP temporal /data/backups | Una a la vez | Retirar tras transferencia externa y comprobacion |

No se crean tareas cron: la API y el worker deben estar detenidos y las cargas
en curso resueltas antes del snapshot. Un servicio cron independiente no debe
suponer que puede montar el mismo volumen. Definir primero el mecanismo de
mantenimiento con acceso al volumen, sin iniciar la API ni su preflight.
Reiniciar la API despues conserva la necesidad de comprobar trabajos
interrumpidos: no existe cola durable ni reintento automatico.

La hora corresponde a Santiago; si se configura un cron UTC, ajustar el horario
por cambios estacionales o usar un programador con zona horaria explicita.
Objetivos propuestos: RPO de 24 h y RTO de 1 jornada de trabajo, sin garantia
hasta probar la recuperacion de base, Auth y originales del mismo punto.

## Secuencia de mantenimiento, todavia sin ejecutar

1. Impedir nuevas cargas, esperar fin de recepciones/trabajos y detener API.
2. Comprobar espacio: originales <=2 GiB, margen para snapshot completo y
   512 MiB de reserva dentro de los 5 GB. Si no cabe, no generar ni borrar;
   resolver capacidad o usar un metodo externo validado.
3. Desde /app, con variables de runtime del servicio, crear un snapshot:

   ```text
   python -m scripts.backup_central --directory /data/backups
   ```

4. Exigir `missing_originals=0` antes de cualquier borrado en este piloto.
   El script verifica CRC y hashes de originales presentes, pero no falla
   automaticamente si faltan originales. Si faltan, no usarlo como autorizacion.
5. Calcular SHA-256 del ZIP final. Cifrarlo y transferirlo al destino privado.
   Descargar una copia, descifrar y comprobar el SHA-256 del ZIP original;
   registrar fecha, tamano, hash y ubicacion sin datos de usuarios ni secretos.
6. Confirmar la copia PostgreSQL/Auth correspondiente. Si no existe cobertura
   recuperable de Auth/base, el respaldo de aplicacion no basta para publicar.
7. Preparar el listado de originales vencidos, sin borrarlos:

   ```text
   python -m scripts.retain_archives --days 30
   ```

8. Revisar el listado y la copia externa. Solo entonces considerar la opcion
   destructiva `--delete-expired`; nunca ejecutarla por calendario sin ese control.
   Resultados e historial quedan en la base.
9. Retirar la copia temporal despues de verificar transferencia y capacidad.
   Aplicar retencion externa sin eliminar el ultimo respaldo recuperable.
10. Reiniciar API y comprobar su estado en la fase de validacion operativa.

## Restauracion propuesta para la proxima fase

Crear base y volumen descartables aislados, sin sobreescribir recursos activos.
Descargar y descifrar copia externa; verificar ZIP, manifiesto y SHA-256.
Preparar esquema con migraciones administrativas; recuperar filas manteniendo
UUID, fechas y JSONB, sin insertar geom generada, y verificar FK/SRID.
Recuperar originales y permisos uid/gid 10001; comparar todos los hashes.
Recuperar Auth con un mecanismo compatible y comprobar que issuer e identidades
se corresponden con vial.users. No basta con crear usuarios con otros UUID.
Autenticar las dos cuentas y comprobar aislamiento y descargas.

Ya existe un restaurador limitado a destinos descartables y probado localmente;
el ensayo PostgreSQL/PostGIS nuevo sigue pendiente de CI. Ver
[RECUPERACION.md](RECUPERACION.md) para alcance, restricciones y resultados.
No es un restaurador general para proyectos Supabase. El mecanismo de
transferencia/cifrado externo sigue pendiente. No activar
`VIAL_PERSISTENT_STORAGE_CONFIRMED=1` por el solo hecho de tener este documento.

Los [backups de volumen Railway](https://docs.railway.com/volumes/backups)
pueden complementar la copia externa. Documentan retenciones de 6 dias
(diarios), 27 dias (semanales) y 89 dias (mensuales), con costo incremental.
No asumen la cobertura de Supabase Auth/base ni sustituyen otra cuenta.
Revisar elegibilidad del plan antes de habilitarlos; no se habilitaron.
