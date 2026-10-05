import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface AlunoTurma {
  id_aluno: string;
  nome: string;
  papel: string;
  gratuito: boolean;
}

interface Turma {
  id: number;
  nome: string;
  tipo_pagamento: string;
  classe: string;
  valor_base: number;
  recorrencia_rrule: string | null;
  recorrencia_descricao: string | null;
  hora_inicio: string | null;
  hora_fim: string | null;
  ativo: boolean;
  alunos: AlunoTurma[];
}

/**
 * Painel de Gestão de Turmas (Fase 1 — frontend que faltava).
 *
 * Permite criar turmas (com um construtor amigável de recorrência que monta a
 * RRULE a partir de dias da semana), listar, vincular/desvincular alunos e
 * gerar as ocorrências do mês no calendário. Consome os endpoints `/turmas` e
 * `/turmas/{id}/ocorrencias/gerar`.
 */
@Component({
  selector: 'app-turmas-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './turmas-panel.component.html',
})
export class TurmasPanelComponent implements OnInit {
  turmas: Turma[] = [];
  alunos: any[] = [];
  carregando = false;

  // Dias da semana -> código RRULE (BYDAY).
  diasSemana = [
    { cod: 'MO', label: 'Seg' },
    { cod: 'TU', label: 'Ter' },
    { cod: 'WE', label: 'Qua' },
    { cod: 'TH', label: 'Qui' },
    { cod: 'FR', label: 'Sex' },
    { cod: 'SA', label: 'Sáb' },
    { cod: 'SU', label: 'Dom' },
  ];

  // Formulário de nova turma.
  exibirForm = false;
  nova = this.formVazio();

  // Vínculo de aluno por turma (id selecionado + papel).
  alunoSelecionado: { [idTurma: number]: string } = {};
  papelSelecionado: { [idTurma: number]: string } = {};

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregar();
    this.api.get('/alunos').subscribe({
      next: (dados: any) => (this.alunos = dados || []),
      error: () => (this.alunos = []),
    });
  }

  formVazio() {
    return {
      nome: '',
      tipo_pagamento: 'Mensalidade',
      classe: 'Dojo',
      valor_base: 30.0,
      hora_inicio: '19:00',
      hora_fim: '21:00',
      dias: {} as { [cod: string]: boolean },
    };
  }

  carregar(): void {
    this.carregando = true;
    this.api.get<Turma[]>('/turmas').subscribe({
      next: (dados) => {
        this.turmas = dados || [];
        this.carregando = false;
      },
      error: () => {
        this.turmas = [];
        this.carregando = false;
      },
    });
  }

  abrirForm(): void {
    this.nova = this.formVazio();
    this.exibirForm = true;
  }

  /** Monta a RRULE a partir dos dias marcados (ex.: FREQ=WEEKLY;BYDAY=SA,TU). */
  private montarRrule(): { rrule: string | null; descricao: string | null } {
    const marcados = this.diasSemana.filter((d) => this.nova.dias[d.cod]);
    if (marcados.length === 0) {
      return { rrule: null, descricao: null };
    }
    const byday = marcados.map((d) => d.cod).join(',');
    const labels = marcados.map((d) => d.label).join(', ');
    return {
      rrule: `FREQ=WEEKLY;BYDAY=${byday}`,
      descricao: `Toda semana: ${labels} (${this.nova.hora_inicio}–${this.nova.hora_fim})`,
    };
  }

  criarTurma(): void {
    if (!this.nova.nome.trim()) {
      alert('Informe o nome da turma.');
      return;
    }
    const { rrule, descricao } = this.montarRrule();
    const payload = {
      nome: this.nova.nome.trim(),
      tipo_pagamento: this.nova.tipo_pagamento,
      classe: this.nova.classe,
      valor_base: this.nova.valor_base,
      recorrencia_rrule: rrule,
      recorrencia_descricao: descricao,
      hora_inicio: this.nova.hora_inicio,
      hora_fim: this.nova.hora_fim,
      alunos: [],
    };
    this.api.post('/turmas', payload).subscribe({
      next: () => {
        alert('Turma criada!');
        this.exibirForm = false;
        this.carregar();
      },
      error: (err) => alert(err?.error?.detail || 'Falha ao criar a turma.'),
    });
  }

  vincularAluno(turma: Turma): void {
    const idAluno = this.alunoSelecionado[turma.id];
    const papel = this.papelSelecionado[turma.id] || 'matriculado';
    if (!idAluno) {
      alert('Selecione um aluno.');
      return;
    }
    this.api
      .post(`/turmas/${turma.id}/alunos`, { id_aluno: idAluno, papel })
      .subscribe({
        next: () => {
          this.alunoSelecionado[turma.id] = '';
          this.carregar();
        },
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao vincular o aluno.'),
      });
  }

  desvincularAluno(turma: Turma, idAluno: string): void {
    if (!confirm('Remover este aluno da turma?')) return;
    this.api.delete(`/turmas/${turma.id}/alunos/${idAluno}`).subscribe({
      next: () => this.carregar(),
      error: () => alert('Falha ao remover o aluno.'),
    });
  }

  gerarOcorrenciasMes(turma: Turma): void {
    if (!turma.recorrencia_rrule) {
      alert('Esta turma não tem recorrência definida.');
      return;
    }
    const hoje = new Date();
    const ano = hoje.getFullYear();
    const mes = hoje.getMonth(); // 0-based
    const inicio = new Date(ano, mes, 1);
    const fim = new Date(ano, mes + 1, 0); // último dia do mês
    const fmt = (d: Date) => d.toISOString().substring(0, 10);
    this.api
      .post(`/turmas/${turma.id}/ocorrencias/gerar`, {
        data_inicio: fmt(inicio),
        data_fim: fmt(fim),
      })
      .subscribe({
        next: (res: any) =>
          alert(
            `${res.geradas} aula(s) gerada(s) para ${turma.nome} neste mês. ` +
              'Veja no Calendário.'
          ),
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao gerar as ocorrências.'),
      });
  }

  desativarTurma(turma: Turma): void {
    if (!confirm(`Desativar a turma "${turma.nome}"?`)) return;
    this.api.delete(`/turmas/${turma.id}`).subscribe({
      next: () => this.carregar(),
      error: () => alert('Falha ao desativar a turma.'),
    });
  }

  formatarMoeda(valor: number): string {
    return (valor || 0).toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  }
}
