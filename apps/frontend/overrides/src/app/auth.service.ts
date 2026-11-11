import { Injectable, computed, signal } from '@angular/core';

const OIDC = 'http://localhost:8080/realms/examen/protocol/openid-connect';
const CLIENT_ID = 'webapp';
const SCOPE = 'openid docs:read docs:write docs:delete';

function b64url(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = '';
  bytes.forEach((b) => (s += String.fromCharCode(b)));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomString(n: number): string {
  const a = new Uint8Array(n);
  crypto.getRandomValues(a);
  return b64url(a);
}

function decode(jwt: string): any {
  const p = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
  return JSON.parse(atob(p + '='.repeat((4 - (p.length % 4)) % 4)));
}

/**
 * Authorization Code + PKCE (S256), ecrit a la main pour bien voir chaque etape.
 * L'etat est dans des signals : l'interface se met a jour toute seule (Angular zoneless).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private tokens = signal<{ a: string; r: string } | null>(null);

  readonly loggedIn = computed(() => this.tokens() !== null);
  readonly claims = computed<any>(() => {
    const t = this.tokens();
    return t ? decode(t.a) : null;
  });

  constructor() {
    this.restore();
  }

  get accessToken(): string | null {
    return this.tokens()?.a ?? null;
  }

  get redirectUri(): string {
    return window.location.origin + '/';
  }

  /** Secondes restantes avant expiration de l'access token. */
  secondsLeft(nowMs: number): number {
    const c = this.claims();
    return c ? Math.round(c.exp - nowMs / 1000) : 0;
  }

  /** Etape 1 : generer code_verifier / code_challenge, rediriger vers Keycloak. */
  async login(): Promise<void> {
    const verifier = randomString(64);
    const state = randomString(16);
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
    sessionStorage.setItem('pkce_verifier', verifier);
    sessionStorage.setItem('pkce_state', state);
    const params = new URLSearchParams({
      client_id: CLIENT_ID,
      response_type: 'code',
      redirect_uri: this.redirectUri,
      scope: SCOPE,
      state,
      code_challenge: b64url(digest),
      code_challenge_method: 'S256',
    });
    window.location.href = `${OIDC}/auth?${params}`;
  }

  /** Etape 2 : au retour de Keycloak, echanger le code (+ code_verifier) contre les jetons. */
  async handleCallback(): Promise<void> {
    const q = new URLSearchParams(window.location.search);
    const code = q.get('code');
    if (!code) return;
    const state = q.get('state');
    const verifier = sessionStorage.getItem('pkce_verifier');
    window.history.replaceState({}, '', '/');
    if (state !== sessionStorage.getItem('pkce_state') || !verifier) {
      throw new Error('state invalide (protection CSRF)');
    }
    sessionStorage.removeItem('pkce_state');
    sessionStorage.removeItem('pkce_verifier');
    await this.tokenRequest({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code,
      redirect_uri: this.redirectUri,
      code_verifier: verifier,
    });
  }

  /** Renouvelle l'access token (le refresh token est a usage unique : rotation). */
  async refresh(): Promise<void> {
    const t = this.tokens();
    if (!t) throw new Error('pas de refresh token');
    try {
      await this.tokenRequest({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: t.r,
      });
    } catch (e) {
      this.clear();
      throw e;
    }
  }

  /** Deconnexion : revocation du refresh token (RFC 7009), puis nettoyage local. */
  async logout(): Promise<void> {
    const t = this.tokens();
    if (t) {
      await fetch(`${OIDC}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          client_id: CLIENT_ID,
          token: t.r,
          token_type_hint: 'refresh_token',
        }),
      }).catch(() => undefined);
    }
    this.clear();
  }

  private async tokenRequest(body: Record<string, string>): Promise<void> {
    const r = await fetch(`${OIDC}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(body),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error_description || data.error || `HTTP ${r.status}`);
    const t = { a: data.access_token as string, r: data.refresh_token as string };
    this.tokens.set(t);
    sessionStorage.setItem('tokens', JSON.stringify(t));
  }

  private restore(): void {
    try {
      const t = JSON.parse(sessionStorage.getItem('tokens') || 'null');
      if (t) {
        decode(t.a); // verifie que le jeton est lisible
        this.tokens.set(t);
      }
    } catch {
      this.clear();
    }
  }

  private clear(): void {
    this.tokens.set(null);
    sessionStorage.removeItem('tokens');
  }
}
