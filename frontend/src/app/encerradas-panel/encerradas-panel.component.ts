import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

/**
 * Painel de Matrículas Encerradas.
 *
 * Lista as matrículas dentro da janela de retenção de 30 dias, com os dias
 * restantes até o expurgo definitivo. Permite:
 * - **Baixar** o dossiê PDF gerado no encerramento;
 * - **Revogar** o encerramento (restaura o aluno ao estado anterior).
 */
@Component({
  selector: 'app-encerradas-panel',
  standalone: true,
  imports: [CommonModule, LucideAngularModule],
  templateUrl: './encerradas-panel.component.html',
})
export class EncerradasPanelComponent implements OnInit {
  encerradas: any[] = [];
  carregando = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.carregando = true;
    this.api.get('/encerramentos').subscribe({
      next: (dados: any) => {
        this.encerradas = dados;
        this.carregando = false;
      },
      error: () => {
        this.carregando = false;
      },
    });
  }

  /** Baixa o dossiê PDF (blob) e dispara o download no navegador. */
  baixarDossie(item: any): void {
    this.api.getBlob(`/alunos/${item.id_matricula}/dossie`).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = item.dossie_nome || `dossie_${item.id_matricula}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      },
      error: () => alert('Não foi possível baixar o dossiê.'),
    });
  }

  /** Revoga o encerramento, restaurando o aluno ao estado anterior. */
  revogar(item: any): void {
    if (
      !confirm(
        `Revogar o encerramento de ${item.nome}? O aluno volta ao estado anterior e o expurgo é cancelado.`
      )
    ) {
      return;
    }
    this.api
      .post(`/alunos/${item.id_matricula}/revogar-encerramento`, {})
      .subscribe({
        next: (res: any) => {
          alert(`Encerramento revogado. Aluno restaurado para: ${res.estado_restaurado}.`);
          this.carregar();
        },
        error: () => alert('Não foi possível revogar o encerramento.'),
      });
  }
}
