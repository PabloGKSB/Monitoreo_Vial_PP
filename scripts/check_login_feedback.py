"""Regression check: a password error must not claim the email is unconfirmed."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    cases = [
        ('invalid_credentials', 'El correo o la contraseña no coinciden.'),
        ('email_not_confirmed', 'Tu correo aún no está confirmado.'),
    ]
    code = cases[0][0]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1200,'height':900})

        def auth_error(route):
            route.fulfill(status=400, content_type='application/json', body=json.dumps({
                'code':code, 'error_code':code, 'msg':'Controlled auth error'}))

        page.route('**/auth/v1/token?grant_type=password', auth_error)
        page.goto('http://127.0.0.1:8001', wait_until='networkidle')
        for code, expected in cases:
            page.locator('#email').fill('prueba@example.test')
            page.locator('#password').fill('ejemplo-de-prueba')
            page.locator('#login').click()
            expect(page.locator('#message')).to_contain_text(expected)
            if code == 'invalid_credentials':
                assert 'confirm' not in page.locator('#message').inner_text().lower()
            expect(page.locator('#workspace')).to_be_hidden()
        output = Path('.api_local/supabase/browser/login-feedback.json')
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({'credential_error_is_distinct':True,
                                      'confirmation_error_is_specific':True}),encoding='utf-8')
        browser.close()
    print('Login feedback regression passed for invalid credentials and unconfirmed email. No real login attempts or emails sent.')


if __name__ == '__main__':
    main()
