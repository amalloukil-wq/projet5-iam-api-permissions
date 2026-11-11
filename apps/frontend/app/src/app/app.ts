import { Component, OnInit, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { JsonPipe } from '@angular/common';
import { AuthService } from './auth.service';

const API = 'http://localhost:8000';

interface LogLine {
  time: string;
  call: string;
  status: number | string;
  body: any;
}

@Component({
  selector: 'app-root',
  imports: [FormsModule, JsonPipe],
  template: `
    <main>
      <h1>Documents : API a permissions fines</h1>

      @if (error()) {
        <p class="err">{{ error() }}</p>
      }

      @if (!auth.loggedIn()) {
        <p>Vous n'etes pas connecte.</p>
        <button (click)="auth.login()">Se connecter (Code + PKCE)</button>
        <button class="sec" (click)="call('GET', '/docs', false)">GET /docs sans jeton</button>
      } @else {
        <section class="card">
          <h2>Jeton</h2>
          <p>
            Utilisateur : <b>{{ auth.claims().preferred_username }}</b> |
            groupes : <b>{{ auth.claims().groups?.join(', ') || 'aucun' }}</b>
          </p>
          <p>Scopes : {{ auth.claims().scope }}</p>
          <p>
            Expire dans :
            <b [class.err]="auth.secondsLeft(now()) <= 0">
              {{ auth.secondsLeft(now()) > 0 ? auth.secondsLeft(now()) + ' s' : 'EXPIRE' }}
            </b>
          </p>
          <button class="sec" (click)="refresh()">Renouveler (refresh token)</button>
          <button class="sec" (click)="auth.logout()">Deconnexion (revocation)</button>
          <details>
            <summary>Claims de l'access token</summary>
            <pre>{{ auth.claims() | json }}</pre>
          </details>
        </section>

        <section class="card">
          <h2>Appels a l'API</h2>
          <p>
            Validation du jeton cote API :
            <select [(ngModel)]="mode">
              <option value="local">local (JWT + JWKS)</option>
              <option value="introspect">introspection (RFC 7662)</option>
            </select>
          </p>
          <button (click)="call('GET', '/docs')">GET /docs</button>
          <span class="row">
            <input [(ngModel)]="title" placeholder="titre du document" />
            <button (click)="create()">POST /docs</button>
          </span>
          <span class="row">
            <input type="number" [(ngModel)]="deleteId" style="width: 5em" />
            <button (click)="call('DELETE', '/docs/' + deleteId())">DELETE /docs/id</button>
          </span>
        </section>
      }

      <section class="card">
        <h2>Journal</h2>
        @for (l of log(); track $index) {
          <div class="line">
            <span class="badge s{{ l.status }}">{{ l.status }}</span>
            <code>{{ l.time }} {{ l.call }}</code>
            <pre>{{ l.body | json }}</pre>
          </div>
        } @empty {
          <p>Aucun appel pour l'instant.</p>
        }
      </section>
    </main>
  `,
  styles: [
    `
      main { font-family: system-ui, sans-serif; max-width: 860px; margin: 0 auto; padding: 16px; }
      .card { border: 1px solid #ccc; border-radius: 8px; padding: 12px 16px; margin: 16px 0; }
      button { margin: 4px 6px 4px 0; padding: 6px 12px; cursor: pointer; }
      .sec { background: #eee; }
      .row { display: inline-block; margin-right: 12px; }
      .err { color: #b00020; }
      .line { border-top: 1px solid #eee; padding: 6px 0; }
      pre { margin: 4px 0; white-space: pre-wrap; font-size: 12px; }
      .badge { display: inline-block; min-width: 2.5em; text-align: center; border-radius: 4px;
               color: #fff; background: #777; padding: 1px 6px; margin-right: 8px; font-weight: bold; }
      .s200, .s201 { background: #2e7d32; }
      .s401 { background: #ef6c00; }
      .s403 { background: #c62828; }
    `,
  ],
})
export class App implements OnInit {
  mode = signal<'local' | 'introspect'>('local');
  title = signal('');
  deleteId = signal<number | null>(1);
  error = signal('');
  now = signal(Date.now());
  log = signal<LogLine[]>([]);

  constructor(
    public auth: AuthService,
    private http: HttpClient,
  ) {}

  async ngOnInit(): Promise<void> {
    try {
      await this.auth.handleCallback();
    } catch (e: any) {
      this.error.set(e.message);
    }
    setInterval(() => this.now.set(Date.now()), 1000);
  }

  async refresh(): Promise<void> {
    try {
      await this.auth.refresh();
      this.error.set('');
    } catch (e: any) {
      this.error.set('Renouvellement refuse : ' + e.message);
    }
  }

  create(): void {
    this.call('POST', '/docs', true, { title: this.title() || 'Nouveau document' });
  }

  call(method: string, path: string, withToken = true, body?: any): void {
    const headers: Record<string, string> = {};
    const token = this.auth.accessToken;
    if (withToken && token) headers['Authorization'] = 'Bearer ' + token;
    const label = `${method} ${path}${withToken ? ' [' + this.mode() + ']' : ' [sans jeton]'}`;
    this.http
      .request(method, `${API}${path}?mode=${this.mode()}`, { body, headers, observe: 'response' })
      .subscribe({
        next: (r) => this.push(label, r.status, r.body),
        error: (e: HttpErrorResponse) => this.push(label, e.status || 'reseau', e.error),
      });
  }

  private push(call: string, status: number | string, body: any): void {
    this.log.update((l) => [{ time: new Date().toLocaleTimeString(), call, status, body }, ...l]);
  }
}
