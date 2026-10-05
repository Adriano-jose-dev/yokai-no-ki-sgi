import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../services/auth.service';
import { AdminDetailComponent } from '../admin-detail/admin-detail.component';
import { EncerradasPanelComponent } from '../encerradas-panel/encerradas-panel.component';
import { CalendarioPanelComponent } from '../calendario-panel/calendario-panel.component';
import { TatameTurmaComponent } from '../tatame-turma/tatame-turma.component';

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
    LucideAngularModule,
    AdminDetailComponent,
    EncerradasPanelComponent,
    CalendarioPanelComponent,
    TatameTurmaComponent,
  ],
  templateUrl: './home.component.html',
})
export class HomeComponent {
  abaAtual:
    | 'tatame'
    | 'secretaria'
    | 'calendario'
    | 'encerradas' = 'tatame';

  constructor(private auth: AuthService, private router: Router) {}

  @HostListener('window:navegarParaSecretaria')
  irParaSecretaria() {
    this.abaAtual = 'secretaria';
  }

  sair(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
