"""Browser acceptance checks using two existing confirmed test accounts.

Does not upload files or write tokens to disk. Screenshots stay in .api_local.
"""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api', default='http://127.0.0.1:8001')
    parser.add_argument('--credentials', type=Path, default=Path('.api_local/supabase/auth-test.private.json'))
    parser.add_argument('--upload-zip', type=Path, help='Optional: creates one additional retained job via the browser')
    args = parser.parse_args()
    accounts = json.loads(args.credentials.read_text(encoding='utf-8'))
    output = Path('.api_local/supabase/browser')
    output.mkdir(parents=True, exist_ok=True)
    report = {'accounts': [], 'console_errors': [], 'refresh_after_401': False}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(viewport={'width':1365, 'height':1000}, locale='es-CL')
        page = context.new_page()
        page.on('pageerror', lambda error: report['console_errors'].append(str(error)))
        refresh_requests = []
        page.on('request', lambda request: refresh_requests.append(True)
                if '/auth/v1/token?grant_type=refresh_token' in request.url else None)
        # Exercise the browser's 401/refresh/retry path with a real Auth refresh.
        first = True

        def once_unauthorized(route):
            nonlocal first
            if first:
                first = False
                route.fulfill(status=401, content_type='application/json', body='{"detail":"Sesion de prueba por renovar"}')
            else:
                route.continue_()

        page.route('**/v1/me', once_unauthorized)
        page.goto(args.api, wait_until='networkidle')
        expect(page.locator('#auth-panel')).to_be_visible()
        page.screenshot(path=str(output/'login.png'), full_page=True)
        for number, account in enumerate(accounts, 1):
            page.locator('#email').fill(account['email'])
            page.locator('#password').fill(account['password'])
            page.locator('#login').click()
            expect(page.locator('#workspace')).to_be_visible(timeout=60000)
            expect(page.locator('#identity')).to_have_text(account['email'])
            expect(page.locator('#jobs button').first).to_be_visible(timeout=60000)
            if number == 1 and args.upload_zip:
                page.locator('#archive').set_input_files({'name':'validacion-navegador.zip',
                    'mimeType':'application/zip', 'buffer':args.upload_zip.read_bytes()})
                page.locator('#upload').click()
                expect(page.locator('#job-status')).to_have_text('Disponible', timeout=120000)
                report['browser_upload'] = True
            else:
                page.locator('#jobs button').first.click()
            expect(page.locator('#map')).to_be_visible(timeout=60000)
            expect(page.locator('#metrics .metric')).to_have_count(4)
            expect(page.locator('#map svg path').first).to_be_visible()
            with page.expect_download(timeout=60000) as downloaded:
                page.locator('#download').click()
            assert downloaded.value.suggested_filename.endswith('.zip')
            assert page.evaluate('Object.keys(localStorage).filter(key => key.includes("supabase") || key.startsWith("sb-")).length') == 0
            assert page.evaluate('Object.keys(sessionStorage).filter(key => key.includes("supabase") || key.startsWith("sb-")).length') == 0
            page.screenshot(path=str(output/f'account-{number}.png'), full_page=True)
            report['accounts'].append({'account':number, 'login':True,'map':True,'download':True,
                                       'tokens_in_web_storage':False})
            page.locator('#logout').click()
            expect(page.locator('#workspace')).to_be_hidden(timeout=30000)
            expect(page.locator('#auth-panel')).to_be_visible()
            expect(page.locator('#message')).to_have_text('Sesión cerrada.', timeout=30000)
        report['refresh_after_401'] = bool(refresh_requests)
        assert report['refresh_after_401']
        assert not report['console_errors'], report['console_errors']
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(output/'login-mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        context.close()
        browser.close()
    (output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
