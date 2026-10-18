"""Create a source-only archive from a reviewed allowlist; never deploy or stage Git."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = {'.env.example', 'deploy/.env.production.example'}
PATTERNS = {
    'private-key': r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----',
    'secret-api-key': r'sb_secret_[A-Za-z0-9_-]{20,}',
    'github-token': r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})',
    'aws-access-key': r'AKIA[A-Z0-9]{16}',
    'jwt': r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}',
}


def main():
    names = [line.strip() for line in (ROOT / 'deploy/release-files.txt').read_text().splitlines()
             if line.strip() and not line.startswith('#')]
    if len(names) != len(set(names)):
        raise SystemExit('Lista de archivos duplicada')
    files, findings = [], []
    for name in names:
        relative = Path(name)
        path = ROOT / relative
        if (relative.is_absolute() or '..' in relative.parts or '\\' in name
                or not path.is_file() or path.resolve().is_relative_to(ROOT) is False
                or any(parent.is_symlink() for parent in (path, *path.parents))):
            raise SystemExit('Archivo no permitido o ausente: ' + name)
        if ((any(part.startswith('.') for part in relative.parts)
             and name not in TEMPLATES and name not in {'.gitignore', '.dockerignore'}
             and relative.parts[0] != '.github')
                or relative.parts[0].lower() in {'data', 'outputs', 'capturas', 'app_apk'}
                or relative.suffix.lower() in {'.zip', '.apk', '.aab', '.db', '.sqlite', '.sqlite3',
                                               '.key', '.pem', '.p12', '.jks', '.keystore', '.pyc'}
                or ('.env' in relative.name and name not in TEMPLATES)):
            raise SystemExit('Artefacto privado o generado no permitido: ' + name)
        content = path.read_bytes()
        text = content.decode('utf-8-sig')
        for line_number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    findings.append({'path': name, 'line': line_number, 'kind': kind})
        files.append({'path': name, 'bytes': len(content), 'sha256': sha256(content).hexdigest()})
    if findings:
        print(json.dumps({'potential_secrets': findings, 'values_printed': False}))
        raise SystemExit('Revisar posibles secretos antes de empaquetar')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8]
    destination = ROOT / '.api_local/deploy' / stamp
    destination.mkdir(parents=True, exist_ok=False)
    with ZipFile(destination / 'source.zip', 'x', compression=ZIP_DEFLATED) as archive:
        for item in files:
            archive.write(ROOT / item['path'], item['path'])
    report = {'files': files, 'total_bytes': sum(item['bytes'] for item in files),
              'pattern_scan_findings': 0,
              'note': 'Source selection only; not application or production validation.'}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'package': destination.relative_to(ROOT).as_posix(),
                      'files': len(files), 'total_bytes': report['total_bytes'],
                      'pattern_scan_findings': 0, 'deployed': False}))


if __name__ == '__main__':
    main()
