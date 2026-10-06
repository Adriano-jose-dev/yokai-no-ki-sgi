import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../services/auth.service';
import { AdminDetailComponent } from '../admin-detail/admin-detail.component';
import { EncerradasPanelComponent } from '../encerradas-panel/encerradas-panel.component';
import { CalendarioPanelComponent } from '../calendario-panel/calendario-panel.component';
import { TatameTurmaComponent } from '../tatame-turma/tatame-turma.component';
import { AuditoriaPanelComponent } from '../auditoria-panel/auditoria-panel.component';
import { TurmasPanelComponent } from '../turmas-panel/turmas-panel.component';

/**
 * Shell principal autenticado do SGI-YKR: cabeçalho, navegação por abas
 * (Ambiente Tatame / Secretaria / Calendário / Encerradas) e botão de logout.
 * O Ambiente Tatame unifica o antigo Modo Tatame e a Presença (presença e
 * cronômetro agora acontecem dentro do fluxo por turma). Protegido pelo authGuard.
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LucideAngularModule,
    AdminDetailComponent,
    EncerradasPanelComponent,
    CalendarioPanelComponent,
    TatameTurmaComponent,
    AuditoriaPanelComponent,
    TurmasPanelComponent,
  ],
  templateUrl: './home.component.html',
})
export class HomeComponent {
  abaAtual:
    | 'tatame'
    | 'secretaria'
    | 'turmas'
    | 'calendario'
    | 'encerradas'
    | 'auditoria' = 'tatame';

  // S2: troca de senha obrigatória no primeiro acesso.
  senhaAtual = '';
  novaSenha = '';
  novaSenhaConfirma = '';
  erroTroca = '';

  constructor(private auth: AuthService, private router: Router) {}

  @HostListener('window:navegarParaSecretaria')
  irParaSecretaria() {
    this.abaAtual = 'secretaria';
  }

  get precisaTrocarSenha(): boolean {
    return this.auth.precisaTrocarSenha;
  }

  confirmarTrocaSenha(): void {
    this.erroTroca = '';
    if (this.novaSenha !== this.novaSenhaConfirma) {
      this.erroTroca = 'A confirmação não confere com a nova senha.';
      return;
    }
    this.auth.trocarSenha(this.senhaAtual, this.novaSenha).subscribe({
      next: () => {
        this.senhaAtual = '';
        this.novaSenha = '';
        this.novaSenhaConfirma = '';
        alert('Senha alterada com sucesso.');
      },
      error: (err) =>
        (this.erroTroca = err?.error?.detail || 'Não foi possível trocar a senha.'),
    });
  }

  sair(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
