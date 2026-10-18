export function loginErrorMessage(error) {
  if (error.code === 'email_not_confirmed') {
    return 'Tu correo aún no está confirmado. Abre el enlace de confirmación recibido por correo.';
  }
  if (error.code === 'invalid_credentials') {
    return 'El correo o la contraseña no coinciden. Usa la contraseña de tu cuenta de Monitoreo Vial.';
  }
  if (error.status === 429) return 'Demasiados intentos. Espera unos minutos antes de volver a entrar.';
  if (error.status >= 500 || error.name === 'AuthRetryableFetchError') {
    return 'El servicio de acceso no está disponible en este momento. Inténtalo nuevamente más tarde.';
  }
  return 'No se pudo iniciar sesión. Inténtalo nuevamente.';
}

/** Session tokens stay in the SDK's memory; only same-origin API requests carry them. */
export class SessionApi {
  constructor(auth, fetcher = fetch) {
    this.auth = auth;
    this.fetcher = fetcher.bind(globalThis);
    this.userId = null;
    this.generation = 0;
    this.controller = new AbortController();
    this.refreshing = null;
  }

  setSession(session) {
    const userId = session?.user?.id ?? null;
    if (userId !== this.userId) {
      this.controller.abort();
      this.controller = new AbortController();
      this.generation += 1;
      this.refreshing = null;
      this.userId = userId;
    }
  }

  async refresh() {
    const generation = this.generation;
    if (!this.refreshing) {
      const promise = this.auth.refreshSession().then(({data, error}) => {
        if (generation !== this.generation) throw new Error('La sesión cambió.');
        if (error || !data.session || data.session.user.id !== this.userId) {
          this.setSession(null);
          throw new Error('La sesión venció. Inicia sesión nuevamente.');
        }
        return data.session;
      }).finally(() => {
        if (this.refreshing === promise) this.refreshing = null;
      });
      this.refreshing = promise;
    }
    return this.refreshing;
  }

  async request(path, options = {}) {
    if (!path.startsWith('/v1/') || path.includes('\\') || path.includes('..')) {
      throw new Error('Ruta de API no admitida.');
    }
    if (!this.userId) throw new Error('Inicia sesión para continuar.');
    const generation = this.generation;
    const signal = this.controller.signal;
    const {data, error} = await this.auth.getSession();
    if (generation !== this.generation) throw new Error('La sesión cambió.');
    if (error || data.session?.user?.id !== this.userId) {
      this.setSession(null);
      throw new Error('La sesión venció. Inicia sesión nuevamente.');
    }
    let session = data.session;
    if ((session.expires_at ?? 0) * 1000 < Date.now() + 60000) session = await this.refresh();
    const send = token => this.fetcher(path, {...options, signal, cache: 'no-store',
      credentials: 'omit', headers: {...options.headers, Authorization: `Bearer ${token}`}});
    let response = await send(session.access_token);
    if (generation !== this.generation) throw new Error('La sesión cambió.');
    if (response.status === 401) {
      session = await this.refresh();
      response = await send(session.access_token);
    }
    if (generation !== this.generation) throw new Error('La sesión cambió.');
    if (response.status === 401) this.setSession(null);
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(typeof payload.detail === 'string' ? payload.detail : `No se pudo completar la solicitud (${response.status}).`);
    }
    return response;
  }

  async signOut() {
    this.setSession(null);
    const {error} = await this.auth.signOut({scope: 'local'});
    if (error) throw new Error('Se cerró la vista local. No se pudo confirmar la revocación remota; vuelve a intentarlo al recuperar la conexión.');
  }
}
