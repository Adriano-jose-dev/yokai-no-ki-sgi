import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';

/**
 * Serviço central de acesso à API do SGI-YKR.
 *
 * Concentra a URL base (vinda de `environment.apiUrl`) em um único ponto, para
 * que nenhum componente precise conhecer o endereço do back-end. Este também é
 * o lugar natural para, na Fase A, adicionar o envio do token JWT via
 * HttpInterceptor sem tocar nos componentes.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) { }

  /** Monta a URL completa a partir de um caminho relativo (com ou sem "/"). */
  private url(path: string): string {
    const normalizado = path.startsWith('/') ? path : `/${path}`;
    return `${this.baseUrl}${normalizado}`;
  }

  get<T = any>(path: string): Observable<T> {
    return this.http.get<T>(this.url(path));
  }

  /** GET que devolve um arquivo binário (ex.: PDF do dossiê). */
  getBlob(path: string): Observable<Blob> {
    return this.http.get(this.url(path), { responseType: 'blob' });
  }

  post<T = any>(path: string, body: any = {}): Observable<T> {
    return this.http.post<T>(this.url(path), body);
  }

  put<T = any>(path: string, body: any = {}): Observable<T> {
    return this.http.put<T>(this.url(path), body);
  }

  delete<T = any>(path: string): Observable<T> {
    return this.http.delete<T>(this.url(path));
  }

  /** Requisição genérica (usada, por ex., para escolher put/post dinamicamente). */
  request<T = any>(method: string, path: string, body: any = {}): Observable<T> {
    return this.http.request<T>(method, this.url(path), { body });
  }
}
