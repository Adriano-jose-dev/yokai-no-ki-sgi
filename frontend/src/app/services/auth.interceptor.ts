import { inject } from '@angular/core';
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/**
 * Interceptor de autenticação funcional (Angular 17).
 *
 * - Injeta `Authorization: Bearer <token>` em todas as requisições, exceto o
 *   próprio login.
 * - Em respostas 401 (token ausente/expirado/inválido), faz logout e
 *   redireciona para a tela de login.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  const token = auth.getToken();
  const ehLogin = req.url.endsWith('/auth/login');

  const requisicao =
    token && !ehLogin
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

  return next(requisicao).pipe(
    catchError((erro: HttpErrorResponse) => {
      if (erro.status === 401 && !ehLogin) {
        auth.logout();
        router.navigate(['/login']);
      }
      return throwError(() => erro);
    })
  );
};
