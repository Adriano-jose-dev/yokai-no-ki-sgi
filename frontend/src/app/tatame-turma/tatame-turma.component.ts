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

  // Cronômetro individual (Hora-Aula) — por aluno.
  sessoesAtivas: { [id: string]: boolean } = {};
  temposIniciais: { [id: string]: number } = {}; // epoch ms do início da sessão
  temposAtuais: { [id: string]: number } = {};
  descontos: { [id: string]: number } = {};

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregarTurmas();
    this.intervalId = setInterval(() => {
      const agora = Date.now();
      if (this.globalRodando) this.globalAgora = agora;
      // Atualiza os cronômetros individuais (Hora-Aula) em andamento.
      for (const id in this.sessoesAtivas) {
        if (this.sessoesAtivas[id]) this.temposAtuais[id] = agora;
      }
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
        this.sessoesAtivas = {};
        this.descontos = {};
        this.localizarOcorrenciaDoDia();
        if (t.tipo_pagamento === 'Hora-Aula') {
          this.sincronizarSessoesAtivas();
        }
      },
    });
  }

  /** Para Hora-Aula: descobre quais alunos da turma já têm sessão aberta. */
  private sincronizarSessoesAtivas(): void {
    this.api.get<any[]>('/tatame/ativos').subscribe({
      next: (ativos) => {
        const idsTurma = new Set((this.turma?.alunos || []).map((a) => a.id_aluno));
        for (const a of ativos || []) {
          if (idsTurma.has(a.id_matricula) && a.hora_entrada) {
            this.sessoesAtivas[a.id_matricula] = true;
            this.temposIniciais[a.id_matricula] = new Date(a.hora_entrada).getTime();
            this.temposAtuais[a.id_matricula] = Date.now();
          }
        }
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

  // --- Cronômetro individual (Hora-Aula) ---
  // Reusa os endpoints de sessão existentes (/sessao/start e /sessao/stop),
  // que já calculam a cobrança por valor base × horas.

  iniciarSessao(idAluno: string): void {
    this.api.post('/sessao/start', { id_matricula: idAluno }).subscribe({
      next: () => {
        this.sessoesAtivas[idAluno] = true;
        this.temposIniciais[idAluno] = Date.now();
        this.temposAtuais[idAluno] = Date.now();
      },
      error: (err) =>
        alert(err?.error?.detail || 'Falha ao iniciar o cronômetro.'),
    });
  }

  pararSessao(idAluno: string): void {
    const payload = {
      id_matricula: idAluno,
      diario_sensei: this.diarios[idAluno] || null,
      desconto_aplicado: this.descontos[idAluno] || 0.0,
    };
    this.api.post('/sessao/stop', payload).subscribe({
      next: (res: any) => {
        const valor = (res?.valor ?? 0).toFixed(2).replace('.', ',');
        alert(`Sessão finalizada!\nPresença confirmada. Valor: R$ ${valor}`);
        this.sessoesAtivas[idAluno] = false;
        this.diarios[idAluno] = '';
        this.descontos[idAluno] = 0;
      },
      error: () => alert('Falha ao encerrar a sessão.'),
    });
  }

  tempoIndividual(idAluno: string): string {
    if (!this.sessoesAtivas[idAluno] || !this.temposIniciais[idAluno]) {
      return '00:00:00';
    }
    const diff = (this.temposAtuais[idAluno] || Date.now()) - this.temposIniciais[idAluno];
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    const p = (n: number) => n.toString().padStart(2, '0');
    return `${p(h)}:${p(m)}:${p(s)}`;
  }
}
