"""Read-only application snapshot plus private originals; excludes Auth/secrets.

This is not a full Supabase backup and does not replace a restore exercise.
"""

from datetime import datetime, timezone
from hashlib import file_digest
import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

from dotenv import load_dotenv
from sqlalchemy import select

from src.database import database_engine, users, trips, jobs, observations


def json_value(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError('Tipo no admitido en el respaldo')


def backup(engine, root, destination):
    root = root.resolve(strict=True)
    with engine.connect() as connection:
        if engine.dialect.name == 'postgresql':
            connection.exec_driver_sql('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        records = {table.name:[dict(row) for row in connection.execute(select(table)).mappings()]
                   for table in (users,trips,jobs,observations)}
    manifest = {'version':'vial-backup-1','schema_revision':'0002_backend_role',
                'created_at':datetime.now(timezone.utc).isoformat(),
                'counts':{name:len(rows) for name,rows in records.items()},
                'originals':{},'missing_originals':[]}
    with ZipFile(destination, 'x', compression=ZIP_DEFLATED) as output:
        output.writestr('records.json',json.dumps(records,default=json_value))
        for row in records['jobs']:
            job_id = str(UUID(str(row['id'])))
            directory = root/job_id
            original = directory/'input.zip'
            if directory.is_symlink() or original.is_symlink():
                raise ValueError('El respaldo no sigue enlaces simbolicos')
            if not original.is_file():
                manifest['missing_originals'].append(job_id)
                continue
            if original.resolve(strict=True).parent.parent != root:
                raise ValueError('Original fuera del almacenamiento configurado')
            with original.open('rb') as source:
                digest = file_digest(source,'sha256').hexdigest()
            if digest != row['sha256']:
                raise ValueError('Un original no coincide con su hash registrado')
            output.write(original,'archives/'+job_id+'/input.zip',compress_type=ZIP_STORED)
            manifest['originals'][job_id] = digest
        output.writestr('manifest.json',json.dumps(manifest))
    with ZipFile(destination) as verify:
        if verify.testzip() is not None:
            raise ValueError('El respaldo no supera la comprobacion CRC')
        for job_id,digest in manifest['originals'].items():
            with verify.open('archives/'+job_id+'/input.zip') as source:
                if file_digest(source,'sha256').hexdigest() != digest:
                    raise ValueError('El respaldo no conserva el hash original')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',default='.env')
    parser.add_argument('--directory',type=Path)
    args = parser.parse_args()
    load_dotenv(args.env_file,override=False)
    directory = args.directory or Path(os.environ.get('VIAL_BACKUP_DIR','.api_local/backups'))
    directory.mkdir(parents=True,exist_ok=True)
    destination = directory/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]+'.zip')
    engine = database_engine(os.environ['VIAL_DATABASE_URL'])
    try:
        manifest = backup(engine,Path(os.environ['VIAL_API_STORAGE']),destination)
    finally:
        engine.dispose()
    print(json.dumps({'backup':str(destination),'counts':manifest['counts'],
                      'originals':len(manifest['originals']),
                      'missing_originals':len(manifest['missing_originals']),'crc_and_sha256_verified':True}))


if __name__ == '__main__':
    main()
