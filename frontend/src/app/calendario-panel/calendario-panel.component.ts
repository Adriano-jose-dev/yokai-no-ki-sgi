import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface Ocorrencia {
  id: number;
  id_turma: number;
  turma_nome: string;
  tipo_pagamento: string | null;
  classe: string | null;
  data: string; // ISO yyyy-mm-dd
  hora_inicio: string | null;
  hora_fim: string | null;
  estado: string;
  origem: string;
  observacao: string | null;
  duracao_prevista_horas: number;
  duracao_real_min: number | null;
  participantes?: { id_aluno: string; nome: string; papel: string }[];
}

interface CelulaDia {
  data: Date | null; // null = célula vazia (preenchimento da grade)
  iso: string;
  noMes: boolean;
  ocorrencias: Ocorrencia[];
}

/**
 * Painel de Calendário (Fase 1c).
 *
 * Exibe um mês com as ocorrências de aula marcadas por "bolinhas" coloridas
 * (cor por tipo de pagamento; cinza se cancelada). Clicar num dia abre o
 * detalhe: turmas, horários, estado, participantes e duração.
 *
 * Modificações de ocorrência (mover, cancelar, excluir) acontecem aqui.
 */
@Component({
  selector: 'app-calendario-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './calendario-panel.component.html',
})
export class CalendarioPanelComponent implements OnInit {
  readonly nomesMes = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ];
  readonly diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  ano!: number;
  mes!: number; // 0-11
  grade: CelulaDia[] = [];
  ocorrenciasDoMes: Ocorrencia[] = [];

  diaSelecionadoIso: string | null = null;
  detalheDia: Ocorrencia[] = [];
  carregando = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    const hoje = new Date();
    this.ano = hoje.getFullYear();
    this.mes = hoje.getMonth();
    this.carregarMes();
  }

  get rotuloMes(): string {
    return `${this.nomesMes[this.mes]} ${this.ano}`;
  }

  mesAnterior(): void {
    if (this.mes === 0) {
      this.mes = 11;
      this.ano--;
    } else {
      this.mes--;
    }
    this.diaSelecionadoIso = null;
    this.carregarMes();
  }

  mesProximo(): void {
    if (this.mes === 11) {
      this.mes = 0;
      this.ano++;
    } else {
      this.mes++;
    }
    this.diaSelecionadoIso = null;
    this.carregarMes();
  }

  private pad(n: number): string {
    return n < 10 ? `0${n}` : `${n}`;
  }

  carregarMes(): void {
    this.carregando = true;
    const inicio = `${this.ano}-${this.pad(this.mes + 1)}-01`;
    const ultimoDia = new Date(this.ano, this.mes + 1, 0).getDate();
    const fim = `${this.ano}-${this.pad(this.mes + 1)}-${this.pad(ultimoDia)}`;

    this.api.get<Ocorrencia[]>(`/ocorrencias?inicio=${inicio}&fim=${fim}`).subscribe({
      next: (dados) => {
        this.ocorrenciasDoMes = dados || [];
        this.montarGrade();
        this.carregando = false;
      },
      error: () => {
        this.ocorrenciasDoMes = [];
        this.montarGrade();
        this.carregando = false;
      },
    });
  }

  private montarGrade(): void {
    const grade: CelulaDia[] = [];
    const primeiroDiaSemana = new Date(this.ano, this.mes, 1).getDay(); // 0=Dom
    const ultimoDia = new Date(this.ano, this.mes + 1, 0).getDate();

    // Agrupa ocorrências por dia ISO.
    const porDia: { [iso: string]: Ocorrencia[] } = {};
    for (const o of this.ocorrenciasDoMes) {
      (porDia[o.data] ||= []).push(o);
    }

    // Células vazias antes do dia 1.
    for (let i = 0; i < primeiroDiaSemana; i++) {
      grade.push({ data: null, iso: '', noMes: false, ocorrencias: [] });
    }
    // Dias do mês.
    for (let d = 1; d <= ultimoDia; d++) {
      const iso = `${this.ano}-${this.pad(this.mes + 1)}-${this.pad(d)}`;
      grade.push({
        data: new Date(this.ano, this.mes, d),
        iso,
        noMes: true,
        ocorrencias: porDia[iso] || [],
      });
    }
    this.grade = grade;
  }

  /** Cor da bolinha por tipo de pagamento (cinza se cancelada). */
  corOcorrencia(o: Ocorrencia): string {
    if (o.estado === 'cancelada') return 'bg-sumi-300';
    return o.tipo_pagamento === 'Mensalidade' ? 'bg-carmesim-500' : 'bg-ouro-500';
  }

  selecionarDia(cel: CelulaDia): void {
    if (!cel.noMes) return;
    this.diaSelecionadoIso = cel.iso;
    this.api.get<Ocorrencia[]>(`/calendario/dia/${cel.iso}`).subscribe({
      next: (dados) => (this.detalheDia = dados || []),
      error: () => (this.detalheDia = []),
    });
  }

  cancelarOcorrencia(o: Ocorrencia): void {
    if (!confirm(`Cancelar a aula de ${o.turma_nome} em ${this.formatarIso(o.data)}?`)) {
      return;
    }
    this.api.post(`/ocorrencias/${o.id}/cancelar`, {}).subscribe({
      next: () => this.recarregarDiaEMes(),
      error: () => alert('Não foi possível cancelar a ocorrência.'),
    });
  }

  excluirOcorrencia(o: Ocorrencia): void {
    if (!confirm(`Excluir definitivamente a aula de ${o.turma_nome} em ${this.formatarIso(o.data)}?`)) {
      return;
    }
    this.api.delete(`/ocorrencias/${o.id}`).subscribe({
      next: () => this.recarregarDiaEMes(),
      error: () => alert('Não foi possível excluir a ocorrência.'),
    });
  }

  private recarregarDiaEMes(): void {
    this.carregarMes();
    if (this.diaSelecionadoIso) {
      const iso = this.diaSelecionadoIso;
      this.api.get<Ocorrencia[]>(`/calendario/dia/${iso}`).subscribe({
        next: (dados) => (this.detalheDia = dados || []),
      });
    }
  }

  formatarIso(iso: string): string {
    const [a, m, d] = iso.split('-');
    return `${d}/${m}/${a}`;
  }
}
