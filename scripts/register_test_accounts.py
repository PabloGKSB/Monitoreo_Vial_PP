"""Register explicitly supplied test emails without printing their passwords."""

import argparse
import json
from pathlib import Path
import secrets

from dotenv import dotenv_values
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('emails', nargs=2)
    args = parser.parse_args()
    if args.emails[0].casefold() == args.emails[1].casefold():
        parser.error('Usar dos direcciones distintas')
    config = dotenv_values('.env')
    destination = Path('.api_local/supabase/auth-test.private.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    accounts = [{'email': email, 'password': secrets.token_urlsafe(32), 'status': 'prepared'}
                for email in args.emails]
    with destination.open('x', encoding='utf-8') as output:
        json.dump(accounts, output)
    with httpx.Client(base_url=config['SUPABASE_URL'],
                      headers={'apikey': config['SUPABASE_PUBLISHABLE_KEY']}, timeout=20) as client:
        for index, account in enumerate(accounts, 1):
            try:
                response = client.post('/auth/v1/signup', json={
                    'email': account['email'], 'password': account['password']})
                payload = response.json()
                if response.is_success:
                    account['status'] = 'confirmation_pending'
                    # An existing-account response can be obfuscated. Only a real login
                    # after email confirmation proves the identity and password.
                    print(json.dumps({'account': index, 'signup_accepted': True,
                                      'confirmation_required': True}))
                else:
                    account['status'] = 'signup_failed'
                    account['error_code'] = payload.get('error_code', payload.get('code'))
                    print(json.dumps({'account': index, 'signup_accepted': False,
                                      'http_status': response.status_code,
                                      'error_code': account['error_code']}))
            except httpx.HTTPError:
                account['status'] = 'network_uncertain'
                print(json.dumps({'account': index, 'signup_accepted': False, 'network_uncertain': True}))
            finally:
                destination.write_text(json.dumps(accounts), encoding='utf-8')


if __name__ == '__main__':
    main()
