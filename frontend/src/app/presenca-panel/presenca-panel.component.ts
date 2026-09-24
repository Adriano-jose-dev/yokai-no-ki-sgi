import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-presenca-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './presenca-panel.component.html'
})
export class PresencaPanelComponent implements OnInit {
  dataFiltro: string = new Date().toISOString().substring(0, 10);
  alunosChamada: any[] = [];

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.carregarChamada();
  }

  carregarChamada(): void {
    this.api.get(`/presenca/diaria/${this.dataFiltro}`).subscribe({
      next: (dados: any) => this.alunosChamada = dados,
      error: (err) => console.error('Erro ao buscar lista de chamada:', err)
    });
  }

  // Altera apenas localmente na tela
  marcarPresenca(idAluno: string, statusNovo: string): void {
    const aluno = this.alunosChamada.find(a => a.id_matricula === idAluno);
    if (aluno) aluno.status = statusNovo;
  }

  // Salva toda a chamada de uma vez no banco
  finalizarAula(): void {
    const payload = {
      data: this.dataFiltro,
      presencas: this.alunosChamada.map(a => ({
        id_aluno: a.id_matricula,
        status: a.status
      }))
    };

    this.api.post('/presenca/bulk', payload).subscribe({
      next: () => alert('Aula finalizada e chamada registrada no histórico com sucesso!'),
      error: (err) => alert('Erro ao salvar a lista de chamada no banco de dados.')
    });
  }
}