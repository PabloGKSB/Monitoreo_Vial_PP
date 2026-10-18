"""Prepare an ignored production env file locally, without network access."""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', help='Exact HTTPS origin once Railway assigns it')
    args = parser.parse_args()
    try:
        local = dotenv_values(ROOT / '.env', interpolate=False)
        values = dotenv_values(ROOT / 'deploy/.env.production.example', interpolate=False)
        required = ('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY', 'VIAL_DATABASE_URL')
        if any(not local.get(key) for key in required):
            raise ValueError('Faltan variables requeridas en .env')
        if not local['SUPABASE_PUBLISHABLE_KEY'].startswith('sb_publishable_'):
            raise ValueError('Se requiere una clave publicable')
        url = make_url(local['VIAL_DATABASE_URL'])
        if not (url.username == 'vial_backend' or (url.username or '').startswith('vial_backend.')):
            raise ValueError('Se requiere el rol vial_backend')
        if url.drivername not in {'postgresql', 'postgresql+psycopg'} or url.query.get('sslmode') != 'verify-full':
            raise ValueError('Se requiere PostgreSQL con verify-full')
        url = url.set(drivername='postgresql+psycopg').update_query_dict(
            {'sslrootcert': '/app/deploy/prod-ca-2021.crt'})
        for key in ('SUPABASE_URL', 'SUPABASE_PUBLISHABLE_KEY'):
            values[key] = local[key]
        values['VIAL_DATABASE_URL'] = url.render_as_string(hide_password=False)
        if args.origin:
            parsed = urlsplit(args.origin)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path not in {'', '/'} or parsed.query or parsed.fragment):
                raise ValueError('El origen debe ser HTTPS sin ruta, consulta ni credenciales')
            values['VIAL_PUBLIC_ORIGIN'] = args.origin.rstrip('/')
        destination = ROOT / '.api_local/deploy/production.env'
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation: never replace an operator's existing secrets.
        with destination.open('x', encoding='utf-8', newline='\n') as output:
            output.write('# Private runtime variables. Never commit or pass to Docker build.\n')
            for key, value in values.items():
                # dotenv single quotes preserve literal $, # and double quotes.
                escaped = str(value).replace('\\', '\\\\').replace("'", "\\'")
                output.write(f"{key}='{escaped}'\n")
        print(json.dumps({'prepared': '.api_local/deploy/production.env',
                          'origin_pending': not bool(args.origin),
                          'persistent_storage_confirmed': False,
                          'network_requests': 0, 'values_printed': False}))
    except FileExistsError:
        parser.exit(1, 'El archivo privado ya existe; no se sobrescribio.\n')
    except Exception:
        # Third-party parser exceptions can include the original DSN.
        parser.exit(1, 'No se pudo preparar el archivo. Revisar variables, rol y TLS localmente; valores omitidos.\n')


if __name__ == '__main__':
    main()
