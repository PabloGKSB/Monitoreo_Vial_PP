import {createClient} from '@supabase/supabase-js';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {SessionApi, loginErrorMessage} from './session.js';

const $ = id => document.getElementById(id);
const statusNames = {QUEUED: 'En espera', PROCESSING: 'Inspeccionando', COMPLETED: 'Disponible', FAILED: 'No completado'};
const qualityNames = {OK: 'Adecuada', WARNING: 'Con avisos', INVALID: 'No utilizable'};
const policyMessages = {
  INVALID_REQUIRED_DATA: 'Los datos requeridos no permiten evaluar este recorrido.',
  NATIVE_DETECTOR_NOT_VALIDATED: 'La detección automática aún no está validada para esta captura.',
  INSPECTION_ONLY: 'Este resultado es una inspección, sin evaluación automática de defectos viales.',
};
let sdk, api, config, offset = 0, selected = null, timer = null, map = null;
let acceptSession = false;

function message(text = '', error = false) {
  $('message').textContent = text;
  $('message').className = error ? 'error' : '';
}

function clearPrivateView() {
  clearTimeout(timer);
  selected = null;
  offset = 0;
  $('workspace').hidden = true;
  $('auth-panel').hidden = false;
  $('identity').textContent = '';
  $('jobs').replaceChildren();
  $('result-panel').hidden = true;
  $('result-title').textContent = '';
  $('job-status').textContent = '';
  $('metrics').replaceChildren();
  $('warnings').replaceChildren();
  $('archive').value = '';
  if (map) { map.remove(); map = null; }
  $('map').hidden = true;
  $('map-note').hidden = true;
}

function report(error) {
  if (error.name === 'AbortError' || error.message === 'La sesión cambió.') return;
  if (!api?.userId) { acceptSession = false; clearPrivateView(); }
  message(error.message || 'No se pudo completar la operación.', true);
}

async function busy(button, action) {
  button.disabled = true;
  message();
  try { await action(); } catch (error) { report(error); }
  finally { button.disabled = false; }
}

async function showSession(session) {
  if (!acceptSession && session) return;
  const changed = api.userId !== (session?.user?.id ?? null);
  api.setSession(session);
  if (!session) { clearPrivateView(); return; }
  if (!changed) return;
  clearPrivateView();
  const identity = await (await api.request('/v1/me')).json();
  if (identity.user_id !== session.user.id || api.userId !== session.user.id) return;
  $('identity').textContent = session.user.email ?? 'Cuenta autenticada';
  $('auth-panel').hidden = true;
  $('workspace').hidden = false;
  await history();
}

async function authenticate(signup) {
  const form = $('auth-form');
  if (!form.reportValidity()) return;
  const email = $('email').value.trim();
  const password = $('password').value;
  $('password').value = '';
  if (signup) {
    const {error} = await sdk.auth.signUp({email, password});
    if (error) throw new Error('No se pudo crear la cuenta. Revisa el correo, la contraseña e inténtalo más tarde.');
    message('Revisa tu correo y confirma la cuenta. Después podrás iniciar sesión aquí.');
    return;
  }
  acceptSession = true;
  const {data, error} = await sdk.auth.signInWithPassword({email, password});
  if (error) { acceptSession = false; throw new Error(loginErrorMessage(error)); }
  sdk.auth.startAutoRefresh();
  await showSession(data.session);
}

async function history() {
  const owner = api.userId;
  const rows = await (await api.request(`/v1/jobs?limit=20&offset=${offset}`)).json();
  if (api.userId !== owner) return;
  $('jobs').replaceChildren();
  $('empty-history').hidden = rows.length > 0;
  $('empty-history').textContent = offset ? 'No hay más recorridos en esta página.' : 'Todavía no tienes recorridos cargados.';
  for (const row of rows) {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.append(document.createTextNode(row.filename));
    const detail = document.createElement('small');
    detail.textContent = `${new Date(row.created_at).toLocaleString('es-CL')} · ${statusNames[row.status]}`;
    button.append(detail);
    button.addEventListener('click', () => selectJob(row.job_id).catch(report));
    item.append(button);
    $('jobs').append(item);
  }
  $('previous').disabled = offset === 0;
  $('next').disabled = rows.length < 20;
  $('page').textContent = `Página ${offset / 20 + 1}`;
}

function metric(label, value) {
  const element = document.createElement('div');
  element.className = 'metric';
  const strong = document.createElement('strong');
  strong.textContent = value;
  const span = document.createElement('span');
  span.textContent = label;
  element.append(strong, span);
  return element;
}

async function selectJob(id) {
  clearTimeout(timer);
  selected = id;
  const owner = api.userId;
  if (map) { map.remove(); map = null; }
  $('map').hidden = true;
  $('map-note').hidden = true;
  $('metrics').replaceChildren();
  $('warnings').replaceChildren();
  const record = await (await api.request(`/v1/jobs/${id}`)).json();
  if (selected !== id || api.userId !== owner) return;
  $('result-panel').hidden = false;
  $('result-title').textContent = record.filename;
  $('job-status').textContent = statusNames[record.status];
  if (record.status === 'FAILED') {
    $('job-status').textContent = record.error?.message ?? 'No se pudo inspeccionar el recorrido.';
    return;
  }
  if (record.status !== 'COMPLETED') {
    timer = setTimeout(() => selectJob(id).catch(report), 2000);
    return;
  }
  const result = await (await api.request(`/v1/jobs/${id}/result`)).json();
  if (selected !== id || api.userId !== owner) return;
  const summary = result.summary;
  $('metrics').append(metric('Calidad de captura', qualityNames[summary.quality_status] ?? 'No disponible'),
    metric('Distancia observada', `${Number(summary.observed_distance_km).toFixed(2)} km`),
    metric('Duración', `${Math.round(summary.duration_seconds)} s`),
    metric('Registros GPS', summary.gps_fix_count));
  const policies = (result.processing_policy?.reasons ?? []).map(reason => policyMessages[reason]).filter(Boolean);
  for (const warning of new Set([...result.warnings, ...policies])) {
    const item = document.createElement('li');
    item.textContent = warning;
    $('warnings').append(item);
  }
  if (result.trajectory.features.length) {
    $('map').hidden = false;
    $('map-note').hidden = false;
    map = L.map('map', {attributionControl: true});
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19,
      attribution: '© OpenStreetMap contributors'}).addTo(map);
    const route = L.geoJSON(result.trajectory, {style: {color: '#245841', weight: 4},
      pointToLayer: (_feature, position) => L.circleMarker(position, {radius: 5, color: '#245841'})}).addTo(map);
    map.fitBounds(route.getBounds(), {padding: [24, 24], maxZoom: 16});
  }
  await history();
}

async function upload() {
  const file = $('archive').files[0];
  if (!file || !file.name.toLowerCase().endsWith('.zip')) throw new Error('Selecciona un archivo ZIP.');
  if (file.size > config.max_upload_bytes) throw new Error('El ZIP supera el límite de carga.');
  const body = new FormData();
  body.append('file', file);
  const owner = api.userId;
  const record = await (await api.request('/v1/jobs', {method: 'POST', body})).json();
  if (api.userId !== owner) return;
  $('archive').value = '';
  offset = 0;
  await history();
  await selectJob(record.job_id);
}

async function download() {
  if (!selected) return;
  const id = selected;
  const response = await api.request(`/v1/jobs/${id}/archive`);
  const blob = await response.blob();
  if (selected !== id || !api.userId) return;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'recorrido-original.zip';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

try {
  const response = await fetch('/v1/client-config', {cache: 'no-store', credentials: 'omit'});
  if (!response.ok) throw new Error('El acceso web no está configurado. Inténtalo más tarde.');
  config = await response.json();
  sdk = createClient(config.supabase_url, config.publishable_key, {auth: {
    persistSession: false, autoRefreshToken: true, detectSessionInUrl: false,
  }});
  api = new SessionApi(sdk.auth);
  sdk.auth.onAuthStateChange((_event, session) => {
    // Avoid awaiting another SDK call while its auth-state lock is held.
    setTimeout(() => showSession(session).catch(report), 0);
  });
  $('upload-limit').textContent = `Máximo ${Math.floor(config.max_upload_bytes / 1024 / 1024)} MB por ZIP.`;
  $('auth-form').addEventListener('submit', event => {
    event.preventDefault(); busy($('login'), () => authenticate(false));
  });
  $('signup').addEventListener('click', () => busy($('signup'), () => authenticate(true)));
  $('logout').addEventListener('click', () => busy($('logout'), async () => {
    acceptSession = false;
    clearPrivateView();
    sdk.auth.stopAutoRefresh();
    await api.signOut();
    message('Sesión cerrada.');
  }));
  $('upload-form').addEventListener('submit', event => {event.preventDefault(); busy($('upload'), upload);});
  $('reload').addEventListener('click', () => busy($('reload'), history));
  $('previous').addEventListener('click', () => {offset = Math.max(0, offset - 20); history().catch(report);});
  $('next').addEventListener('click', () => {offset += 20; history().catch(report);});
  $('download').addEventListener('click', () => busy($('download'), download));
} catch (error) {
  $('login').disabled = true;
  $('signup').disabled = true;
  report(error);
}
