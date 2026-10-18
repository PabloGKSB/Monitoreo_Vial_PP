import test from 'node:test';
import assert from 'node:assert/strict';
import {SessionApi} from '../session.js';

const session = (token = 'initial', owner = 'owner-a') => ({access_token: token,
  expires_at: Math.floor(Date.now() / 1000) + 3600, user: {id: owner}});

function fixture(fetcher, initial = session()) {
  let refreshes = 0;
  const auth = {
    getSession: async () => ({data: {session: initial}}),
    refreshSession: async () => { refreshes++; return {data: {session: session('renewed')}}; },
    signOut: async () => ({}),
  };
  const api = new SessionApi(auth, fetcher);
  api.setSession(initial);
  return {api, auth, refreshes: () => refreshes};
}

test('uses bearer headers and retries a 401 once with the renewed session', async () => {
  const calls = [];
  const f = fixture(async (path, options) => {
    calls.push({path, options});
    return new Response('{}', {status: calls.length === 1 ? 401 : 200});
  });
  await f.api.request('/v1/jobs');
  assert.equal(f.refreshes(), 1);
  assert.equal(calls[0].options.headers.Authorization, 'Bearer initial');
  assert.equal(calls[1].options.headers.Authorization, 'Bearer renewed');
  assert.equal(calls[1].options.credentials, 'omit');
});

test('deduplicates renewal for simultaneous requests near expiry', async () => {
  const expired = {...session(), expires_at: 1};
  const f = fixture(async () => new Response('{}'), expired);
  await Promise.all([f.api.request('/v1/jobs'), f.api.request('/v1/me')]);
  assert.equal(f.refreshes(), 1);
});

test('does not retry an upload after a network failure', async () => {
  let calls = 0;
  const f = fixture(async () => {calls++; throw new TypeError('network unavailable');});
  await assert.rejects(f.api.request('/v1/jobs', {method: 'POST', body: new FormData()}));
  assert.equal(calls, 1);
});

test('never attaches a token to an external or escaped URL', async () => {
  const f = fixture(async () => assert.fail('must not fetch'));
  for (const path of ['https://example.com/v1/jobs', '//example.com/v1/jobs', '/v1/../other', '/v1/\\example.com']) {
    await assert.rejects(f.api.request(path), /Ruta/);
  }
});

test('discards a late response from the previous account', async () => {
  let complete;
  const f = fixture(() => new Promise(resolve => {complete = resolve;}));
  const pending = f.api.request('/v1/jobs');
  await new Promise(resolve => setTimeout(resolve, 0));
  f.api.setSession(session('other', 'owner-b'));
  complete(new Response('{}'));
  await assert.rejects(pending, /sesión cambió/);
});

test('clears local access even when remote sign-out fails', async () => {
  const f = fixture(async () => assert.fail('must not fetch'));
  f.auth.signOut = async () => ({error: new Error('offline')});
  await assert.rejects(f.api.signOut(), /revocación remota/);
  assert.equal(f.api.userId, null);
  await assert.rejects(f.api.request('/v1/jobs'), /Inicia sesión/);
});

test('an unsuccessful refresh removes private access', async () => {
  const f = fixture(async () => new Response('{}', {status: 401}));
  f.auth.refreshSession = async () => ({data: {session: null}, error: new Error('revoked')});
  await assert.rejects(f.api.request('/v1/jobs'), /sesión venció/);
  assert.equal(f.api.userId, null);
});
