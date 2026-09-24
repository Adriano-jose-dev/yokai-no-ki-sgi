import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './login.component.html',
})
export class LoginComponent {
  username = '';
  senha = '';
  erro = '';
  carregando = false;

  constructor(private auth: AuthService, private router: Router) {}

  entrar(): void {
    this.erro = '';
    if (!this.username.trim() || !this.senha) {
      this.erro = 'Informe usuário e senha.';
      return;
    }

    this.carregando = true;
    this.auth.login(this.username.trim(), this.senha).subscribe({
      next: () => {
        this.carregando = false;
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.carregando = false;
        this.erro =
          err?.status === 401
            ? 'Usuário ou senha inválidos.'
            : 'Não foi possível conectar. Tente novamente.';
      },
    });
  }
}
