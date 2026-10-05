import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface Turma {
  id: number;
  nome: string;
  tipo_pagamento: string;
  classe: string;
  valor_base: number;
  alunos: { id_aluno: string; nome: string; papel: string; gratuito: boolean }[];
}

/**
 * Modo Tatame por Turma (Fase 1d).
 *
 * O admin escolhe a turma; o sistema localiza (ou cria) a ocorrência do dia e
 * ajusta o layout conforme o tipo de pagamento:
 *
 * - **Mensalidade**: cronômetro GLOBAL (canto) — validação da duração da aula,
 *   sem efeito financeiro. Cada card de aluno tem botão Presença/Ausência e o
 *   diário do Sensei (no lugar do cronômetro individual).
 * - **Hora-Aula**: cada card tem cronômetro individual (comportamento legado,
 *   cobrança por `valor_base × horas`).
 */
@Component({
  selector: 'app-tatame-turma',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './tatame-turma.component.html',
})
export class TatameTurmaComponent implements OnInit, OnDestroy {
  turmas: Turma[] = [];
  turmaSelecionadaId: number | null = null;
  turma: Turma | null = null;

  // Ocorrência do dia para a turma selecionada.
  ocorrenciaId: number | null = null;
  dataHoje = new Date().toISOString().substring(0, 10);

  // Estado por aluno.
  presencas: { [id: string]: 'Presente' | 'Ausente' | null } = {};
  diarios: { [id: string]: string } = {};

  // Cronômetro global (Mensalidade).
  globalRodando = false;
  globalInicio = 0;
  globalAgora = 0;
  intervalId: any;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregarTurmas();
    this.intervalId = setInterval(() => {
      if (this.globalRodando) this.globalAgora = Date.now();
    }, 1000);
  }

  ngOnDestroy(): void {
    if (this.intervalId) clearInterval(this.intervalId);
  }

  carregarTurmas(): void {
    this.api.get<Turma[]>('/turmas').subscribe({
      next: (dados) => (this.turmas = dados || []),
      error: () => (this.turmas = []),
    });
  }

  get ehMensalidade(): boolean {
    return this.turma?.tipo_pagamento === 'Mensalidade';
  }

  selecionarTurma(): void {
    if (this.turmaSelecionadaId == null) {
      this.turma = null;
      return;
    }
    this.api.get<Turma>(`/turmas/${this.turmaSelecionadaId}`).subscribe({
      next: (t) => {
        this.turma = t;
        this.presencas = {};
        this.diarios = {};
        this.localizarOcorrenciaDoDia();
      },
    });
  }

  /** Procura a ocorrência prevista da turma hoje; se não houver, oferece criar. */
  private localizarOcorrenciaDoDia(): void {
    this.ocorrenciaId = null;
    this.api.get<any[]>(`/calendario/dia/${this.dataHoje}`).subscribe({
      next: (ocs) => {
        const oc = (ocs || []).find((o) => o.id_turma === this.turma?.id);
        this.ocorrenciaId = oc ? oc.id : null;
      },
    });
  }

  criarOcorrenciaHoje(): void {
    if (!this.turma) return;
    this.api
      .post('/ocorrencias/avulsa', { id_turma: this.turma.id, data: this.dataHoje })
      .subscribe({
        next: (oc: any) => {
          this.ocorrenciaId = oc.id;
          alert('Aula de hoje criada.');
        },
        error: () => alert('Não foi possível criar a aula de hoje.'),
      });
  }

  // --- Cronômetro global (Mensalidade) ---

  iniciarGlobal(): void {
    this.globalRodando = true;
    this.globalInicio = Date.now();
    this.globalAgora = Date.now();
  }

  pararGlobal(): void {
    this.globalRodando = false;
    const minutos = Math.round((Date.now() - this.globalInicio) / 60000);
    if (this.ocorrenciaId) {
      this.api
        .put(`/ocorrencias/${this.ocorrenciaId}/duracao`, { duracao_real_min: minutos })
        .subscribe({
          next: () => alert(`Duração registrada: ${minutos} min (validação da aula).`),
        });
    }
  }

  get tempoGlobal(): string {
    if (!this.globalRodando) return '00:00:00';
    const diff = this.globalAgora - this.globalInicio;
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    const p = (n: number) => n.toString().padStart(2, '0');
    return `${p(h)}:${p(m)}:${p(s)}`;
  }

  // --- Presença (Mensalidade) ---

  marcarPresenca(idAluno: string, presente: boolean): void {
    if (!this.ocorrenciaId) {
      alert('Crie a aula de hoje antes de registrar presença.');
      return;
    }
    this.api
      .post(`/ocorrencias/${this.ocorrenciaId}/presenca`, {
        id_aluno: idAluno,
        presente,
        diario_sensei: this.diarios[idAluno] || null,
      })
      .subscribe({
        next: () => (this.presencas[idAluno] = presente ? 'Presente' : 'Ausente'),
        error: () => alert('Falha ao registrar presença.'),
      });
  }
}
