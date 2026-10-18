"""Exercise a running API with two confirmed Auth accounts; never print tokens.

Creates one retained test job per account. It does not migrate the database,
restart the worker or remove users' data.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

from dotenv import dotenv_values
import httpx


class CheckFailed(Exception):
    pass


def require(condition, description):
    if not condition:
        raise CheckFailed(description)


def check_accounts(api_url, zip_path, credentials_path, report_path):
    parsed = urlparse(api_url)
    require(parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in {'127.0.0.1', 'localhost'}),
            'Usar HTTPS o una API local en loopback')
    require(not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.path in {'', '/'}, 'La URL debe ser un origen sin credenciales ni rutas')
    config = dotenv_values('.env')
    accounts = json.loads(credentials_path.read_text(encoding='utf-8'))
    require(len(accounts) == 2, 'Se requieren dos cuentas')
    payload = zip_path.read_bytes()
    require(0 < len(payload) <= 64*1024*1024 and zip_path.suffix.lower() == '.zip', 'ZIP no admitido')
    digest = sha256(payload).hexdigest()
    report = {'accounts': [], 'cross_account_checks': 0, 'archive_sha256': digest}
    sessions = []
    started = time.monotonic()
    with httpx.Client(base_url=config['SUPABASE_URL'], headers={'apikey': config['SUPABASE_PUBLISHABLE_KEY']},
                      timeout=30) as auth, httpx.Client(base_url=api_url, timeout=60) as api:
        require(api.get('/health').status_code == 200, 'La API no esta disponible')
        require(api.get('/v1/jobs').status_code == 401, 'El historial admite acceso sin sesion')
        try:
            for number, account in enumerate(accounts, 1):
                response = auth.post('/auth/v1/token?grant_type=password', json={
                    'email': account['email'], 'password': account['password']})
                require(response.is_success, f'Cuenta {number}: no se pudo iniciar sesion; revisar confirmacion de correo')
                session = response.json()
                sessions.append(session)
                headers = {'Authorization': 'Bearer '+session['access_token']}
                identity = api.get('/v1/me', headers=headers)
                require(identity.status_code == 200 and identity.json()['user_id'] == session['user']['id'],
                        f'Cuenta {number}: identidad no verificada por la API')
                before = time.monotonic()
                upload = api.post('/v1/jobs', headers=headers,
                                  files={'file': ('validacion-integrada.zip', payload, 'application/zip')})
                require(upload.status_code == 202, f'Cuenta {number}: la carga no fue aceptada ({upload.status_code})')
                job_id = upload.json()['job_id']
                deadline = time.monotonic() + 180
                while True:
                    response = api.get(f'/v1/jobs/{job_id}', headers=headers)
                    require(response.status_code == 200, 'No se pudo consultar el trabajo propio')
                    record = response.json()
                    if record['status'] in {'COMPLETED', 'FAILED'}:
                        break
                    require(time.monotonic() < deadline, 'El procesamiento excedio el tiempo de prueba')
                    time.sleep(.5)
                require(record['status'] == 'COMPLETED', f'Cuenta {number}: inspeccion no completada')
                result = api.get(f'/v1/jobs/{job_id}/result', headers=headers)
                require(result.status_code == 200, 'Resultado no disponible')
                require(result.json()['analysis_mode'] == 'inspection', 'Modo de procesamiento inesperado')
                map_response = api.get(f'/v1/jobs/{job_id}/map', headers=headers)
                require(map_response.status_code == 200 and 'L.map(' in map_response.text, 'Mapa no disponible')
                require(map_response.headers.get('Referrer-Policy') == 'no-referrer', 'Mapa sin proteccion de referrer')
                archive = api.get(f'/v1/jobs/{job_id}/archive', headers=headers)
                require(archive.status_code == 200 and sha256(archive.content).hexdigest() == digest,
                        'El ZIP descargado no coincide con el original')
                history = api.get('/v1/jobs?limit=100', headers=headers)
                require(history.status_code == 200 and job_id in {item['job_id'] for item in history.json()},
                        'El trabajo no aparece en el historial propio')
                renewed = auth.post('/auth/v1/token?grant_type=refresh_token', json={'refresh_token':session['refresh_token']})
                require(renewed.is_success, f'Cuenta {number}: renovacion de sesion fallida')
                session = renewed.json()
                sessions[-1] = session
                renewed_identity = api.get('/v1/me', headers={'Authorization':'Bearer '+session['access_token']})
                require(renewed_identity.status_code == 200
                        and renewed_identity.json()['user_id'] == identity.json()['user_id'],
                        'La sesion renovada no conserva la identidad')
                report['accounts'].append({'account':number, 'job_id':job_id,
                    'status':record['status'], 'capture_profile':result.json()['capture_profile'],
                    'seconds':round(time.monotonic()-before, 2), 'session_refreshed':True})
            require(sessions[0]['user']['id'] != sessions[1]['user']['id'], 'Las cuentas no son distintas')
            for index, session in enumerate(sessions):
                headers = {'Authorization':'Bearer '+session['access_token']}
                foreign = report['accounts'][1-index]['job_id']
                history = api.get('/v1/jobs?limit=100', headers=headers)
                require(history.status_code == 200 and foreign not in {item['job_id'] for item in history.json()},
                        'El historial expone un trabajo ajeno')
                for suffix in ['', '/result', '/map', '/archive']:
                    require(api.get(f'/v1/jobs/{foreign}{suffix}', headers=headers).status_code == 404,
                            'Se pudo acceder a un recurso ajeno')
                    report['cross_account_checks'] += 1
            report['distinct_identities'] = True
        finally:
            for number, session in enumerate(sessions, 1):
                logout = auth.post('/auth/v1/logout?scope=local', headers={'Authorization':'Bearer '+session['access_token']})
                require(logout.is_success, f'Cuenta {number}: cierre remoto no confirmado')
                revoked = auth.post('/auth/v1/token?grant_type=refresh_token', json={'refresh_token':session['refresh_token']})
                require(revoked.status_code in {400, 401, 403}, 'Se pudo renovar una sesion cerrada')
            report['sessions_signed_out'] = len(sessions)
    report['total_seconds'] = round(time.monotonic()-started, 2)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='http://127.0.0.1:8001')
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--credentials', type=Path, default=Path('.api_local/supabase/auth-test.private.json'))
    parser.add_argument('--report', type=Path, default=Path('.api_local/supabase/e2e-report.json'))
    args = parser.parse_args()
    try:
        report = check_accounts(args.api, args.zip, args.credentials, args.report)
    except (CheckFailed, httpx.HTTPError) as exc:
        # HTTP exceptions only contain URLs/status; request bodies and tokens are never printed.
        print('Validacion no completada: '+str(exc), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
