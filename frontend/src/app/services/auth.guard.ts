import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';

/**
 * Guard de rota funcional (Angular 17).
 *
 * Libera a navegação apenas para usuários autenticados; caso contrário,
 * redireciona para `/login`.
 */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAutenticado()) {
    return true;
  }
  return router.createUrlTree(['/login']);
};
