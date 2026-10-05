import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface LancamentoExtrato {
  id: number;
  tipo: 'debito' | 'credito';
  categoria: string;
  descricao: string | null;
  valor: number;
  valor_aberto: number;
  status: string;
  data_competencia: string;
  data_vencimento: string | null;
  mes_referencia: string | null;
}

interface ContaCorrente {
  id_aluno: string;
  valores_em_aberto: number;
  credito_disponivel: number;
  saldo_liquido: number;
  extrato: LancamentoExtrato[];
}

/**
 * Painel de Conta Corrente (Fase 2 — Financeiro).
 *
 * Mostra o saldo do aluno como conta corrente (valores em aberto × crédito),
 * o extrato de lançamentos e as ações da fase: gerar/recalcular a mensalidade
 * do mês (a partir do calendário) e registrar um pagamento (crédito que abate
 * débitos). Consome os endpoints `/financeiro/*`.
 *
 * É autônomo: recebe o `idAluno` por @Input e se recarrega quando ele muda.
 */
@Component({
  selector: 'app-conta-corrente-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './conta-corrente-panel.component.html',
})
export class ContaCorrentePanelComponent implements OnChanges {
  @Input() idAluno: string | null = null;
  /** `true` quando o aluno é mensalista (habilita gerar mensalidade/abono). */
  @Input() ehMensalista = false;

  conta: ContaCorrente | null = null;
  previsao: any = null;
  carregando = false;

  // Modal de pagamento na conta corrente.
  exibirModalPagar = false;
  valorPagar = 0;
  metodoPagar = 'Pix';

  // Abono de falta.
  exibirModalAbono = false;
  justificativaAbono = '';

  constructor(private api: ApiService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['idAluno'] && this.idAluno) {
      this.carregar();
    }
  }

  carregar(): void {
    if (!this.idAluno) return;
    this.carregando = true;
    this.api.get<ContaCorrente>(`/financeiro/${this.idAluno}/conta`).subscribe({
      next: (c) => {
        this.conta = c;
        this.carregando = false;
      },
      error: () => (this.carregando = false),
    });
    if (this.ehMensalista) {
      this.api.get(`/financeiro/${this.idAluno}/mensalidade/previsao`).subscribe({
        next: (p) => (this.previsao = p),
        error: () => (this.previsao = null),
      });
    }
  }

  formatarMoeda(valor: number): string {
    return (valor || 0).toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  }

  gerarMensalidade(): void {
    if (!this.idAluno) return;
    this.api
      .post(`/financeiro/${this.idAluno}/mensalidade/gerar`, {})
      .subscribe({
        next: (res: any) => {
          alert(
            `Mensalidade ${res.mes_referencia} gerada: ` +
              `${this.formatarMoeda(res.valor)} (${res.aulas} aulas, ` +
              `venc. ${res.data_vencimento}).`
          );
          this.carregar();
        },
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao gerar a mensalidade.'),
      });
  }

  confirmarPagamento(): void {
    if (!this.idAluno) return;
    if (this.valorPagar <= 0) {
      alert('O valor deve ser maior que zero.');
      return;
    }
    this.api
      .post(`/financeiro/${this.idAluno}/pagar`, {
        valor: this.valorPagar,
        metodo: this.metodoPagar,
      })
      .subscribe({
        next: (res: any) => {
          const sobra = res?.credito_restante ?? 0;
          alert(
            sobra > 0
              ? `Pagamento registrado. Crédito restante: ${this.formatarMoeda(sobra)}.`
              : 'Pagamento registrado e aplicado aos débitos.'
          );
          this.exibirModalPagar = false;
          this.valorPagar = 0;
          this.carregar();
        },
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao registrar o pagamento.'),
      });
  }

  confirmarAbono(): void {
    if (!this.idAluno) return;
    this.api
      .post(`/financeiro/abono`, {
        id_aluno: this.idAluno,
        justificativa: this.justificativaAbono || null,
      })
      .subscribe({
        next: () => {
          alert('Falta abonada (não altera o valor da mensalidade).');
          this.exibirModalAbono = false;
          this.justificativaAbono = '';
        },
        error: (err) =>
          alert(err?.error?.detail || 'Falha ao abonar a falta.'),
      });
  }

  rotuloCategoria(cat: string): string {
    const mapa: { [k: string]: string } = {
      mensalidade: 'Mensalidade',
      hora_aula: 'Hora-Aula',
      taxa_admissao: 'Taxa de Admissão',
      pagamento: 'Pagamento',
      ajuste: 'Ajuste',
    };
    return mapa[cat] || cat;
  }
}
