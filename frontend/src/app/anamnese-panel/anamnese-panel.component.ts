import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface CondicaoCritica {
  chave: string;
  label: string;
  severidade: 'alta' | 'media';
}

interface CardAlerta {
  tem_alerta: boolean;
  condicoes: CondicaoCritica[];
  observacao: string;
  contato_emergencia: {
    nome: string | null;
    parentesco: string | null;
    telefone: string | null;
  };
  validade: {
    data_validade: string | null;
    status: 'ok' | 'vence_em_breve' | 'vencida';
    dias_restantes: number | null;
  };
  versao: number;
  data_preenchimento: string;
}

interface VersaoAnamnese {
  id: number;
  versao: number;
  ativa: boolean;
  data_preenchimento: string;
  validade_meses: number;
  data_validade: string | null;
  respostas: { [chave: string]: string };
  observacao: string | null;
  autor: string | null;
}

/**
 * Painel de Anamnese (Fase 3 — Prontuário médico versionado).
 *
 * Dois papéis:
 * 1. **Card de alerta crítico** — destaque estilo post-it no topo do perfil,
 *    com as condições que interferem na aula, contatos de emergência e o status
 *    de validade (vencida / vence em breve / ok).
 * 2. **Prontuário versionado** — formulário para registrar uma nova versão
 *    (perguntas + validade 6/12 meses) e o histórico de versões anteriores.
 *
 * Autônomo: recebe `idAluno` por @Input e se recarrega quando ele muda.
 */
@Component({
  selector: 'app-anamnese-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './anamnese-panel.component.html',
})
export class AnamnesePanelComponent implements OnChanges {
  @Input() idAluno: string | null = null;
  /** Quando `true`, renderiza SÓ o card de alerta crítico (uso no Resumo). */
  @Input() somenteAlerta = false;

  // Catálogo de perguntas — idêntico à ficha física da Yōkai no Ki Ryūha.
  perguntas = [
    { chave: 'problemas_cardiacos', label: 'Algum médico já lhe disse que possui um problema cardíaco e que só deveria realizar atividade física sob supervisão médica?' },
    { chave: 'dores_peito_atividade', label: 'Sente dores no peito quando pratica atividade física?' },
    { chave: 'dores_peito_repouso', label: 'No último mês, sentiu dores no peito ao realizar atividades físicas ou em repouso?' },
    { chave: 'tontura_desmaio', label: 'Apresenta desequilíbrio devido a tonturas ou já perdeu a consciência/desmaiou alguma vez?' },
    { chave: 'problema_osseo_articular', label: 'Possui algum problema ósseo ou articular (ex: costas, joelhos, ombros, virilha) que pode agravar-se com a prática de artes marciais ou com o uso de armamento de treino?' },
    { chave: 'condicao_respiratoria', label: 'Sofre de alguma condição respiratória (ex: asma, bronquite) que exija cuidados ao ar livre?' },
    { chave: 'medicacao_pressao_cardiaco', label: 'Toma atualmente alguma medicação contínua para a pressão arterial ou problema cardíaco?' },
    { chave: 'cirurgia_recente', label: 'Passou por alguma cirurgia recente?' },
    { chave: 'outra_razao_medica', label: 'Sabe de alguma outra razão física, médica ou psicológica pela qual não deva praticar atividades físicas intensas?' },
  ];

  card: CardAlerta | null = null;
  ativa: VersaoAnamnese | null = null;
  historico: VersaoAnamnese[] = [];
  carregando = false;

  // Formulário de nova versão.
  exibirForm = false;
  respostas: { [chave: string]: string } = {};
  observacao = '';
  validadeMeses = 12;

  constructor(private api: ApiService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['idAluno'] && this.idAluno) {
      this.carregar();
    }
  }

  carregar(): void {
    if (!this.idAluno) return;
    this.carregando = true;
    this.api.get(`/anamnese/${this.idAluno}`).subscribe({
      next: (res: any) => {
        this.card = res.card_alerta;
        this.ativa = res.ativa;
        this.carregando = false;
      },
      error: () => (this.carregando = false),
    });
    this.api.get<VersaoAnamnese[]>(`/anamnese/${this.idAluno}/historico`).subscribe({
      next: (h) => (this.historico = h || []),
      error: () => (this.historico = []),
    });
  }

  abrirForm(): void {
    // Pré-preenche com a versão ativa (facilita a refação).
    this.respostas = {};
    this.perguntas.forEach((p) => (this.respostas[p.chave] = 'nao'));
    if (this.ativa?.respostas) {
      for (const chave of Object.keys(this.ativa.respostas)) {
        this.respostas[chave] = this.ativa.respostas[chave];
      }
    }
    this.observacao = this.ativa?.observacao || '';
    this.validadeMeses = this.ativa?.validade_meses || 12;
    this.exibirForm = true;
  }

  salvar(): void {
    if (!this.idAluno) return;
    this.api
      .post(`/anamnese/${this.idAluno}`, {
        respostas: this.respostas,
        observacao: this.observacao || null,
        validade_meses: this.validadeMeses,
      })
      .subscribe({
        next: (res: any) => {
          alert(`Anamnese versão ${res.versao} registrada (válida até ${res.data_validade}).`);
          this.exibirForm = false;
          this.carregar();
        },
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao salvar a anamnese.'),
      });
  }

  rotuloValidade(status: string): string {
    const mapa: { [k: string]: string } = {
      ok: 'Em dia',
      vence_em_breve: 'Vence em breve',
      vencida: 'Vencida',
    };
    return mapa[status] || status;
  }
}
