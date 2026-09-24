import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';

import { environment } from '../../environments/environment';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

/**
 * Serviço de autenticação do SGI-YKR (Fase A / Requisito 6.7).
 *
 * O login segue o **OAuth2 password flow**: envia as credenciais como
 * `application/x-www-form-urlencoded` (campos `username` e `password`), no
 * padrão oficial esperado pelo back-end e por clientes mobile (APK). O token
 * é guardado no localStorage; o envio dele nas requisições é feito pelo
 * `authInterceptor`, então os componentes não se preocupam com isso.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'ynk_token';
  private readonly baseUrl = environment.apiUrl;

  // Estado reativo para a UI (ex.: alternar login/shell no AppComponent).
  private readonly autenticadoSubject = new BehaviorSubject<boolean>(this.temToken());
  readonly autenticado$ = this.autenticadoSubject.asObservable();

  constructor(private http: HttpClient) {}

  login(username: string, senha: string): Observable<TokenResponse> {
    // Corpo no formato OAuth2 (form-urlencoded), não JSON.
    const corpo = new HttpParams()
      .set('grant_type', 'password')
      .set('username', username)
      .set('password', senha);

    const headers = new HttpHeaders({
      'Content-Type': 'application/x-www-form-urlencoded',
    });

    return this.http
      .post<TokenResponse>(`${this.baseUrl}/auth/login`, corpo.toString(), {
        headers,
      })
      .pipe(
        tap((res) => {
          localStorage.setItem(this.TOKEN_KEY, res.access_token);
          this.autenticadoSubject.next(true);
        })
      );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    this.autenticadoSubject.next(false);
  }

  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  isAutenticado(): boolean {
    return this.temToken();
  }

  private temToken(): boolean {
    return !!localStorage.getItem(this.TOKEN_KEY);
  }
}
