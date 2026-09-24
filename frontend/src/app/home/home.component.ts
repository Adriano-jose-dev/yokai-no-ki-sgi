import { Component, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';

import { AuthService } from '../services/auth.service';
import { DailyPanelComponent } from '../daily-panel/daily-panel.component';
import { PresencaPanelComponent } from '../presenca-panel/presenca-panel.component';
import { AdminDetailComponent } from '../admin-detail/admin-detail.component';

/**
 * Shell principal autenticado do SGI-YKR: cabeçalho, navegação por abas
 * (Tatame / Presença / Secretaria) e botão de logout. Protegido pelo authGuard.
 */
@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    LucideAngularModule,
    DailyPanelComponent,
    PresencaPanelComponent,
    AdminDetailComponent,
  ],
  templateUrl: './home.component.html',
})
export class HomeComponent {
  abaAtual: 'tatame' | 'secretaria' | 'presenca' = 'tatame';

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
