import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

interface EventoAuditoria {
  id: number;
  categoria: 'geral' | 'sensivel';
  acao: string;
  id_aluno: string | null;
  autor: string | null;
  descricao: string | null;
  detalhes: any;
  criado_em: string;
}

/**
 * Painel de Auditoria (Fase 4 — Log de segurança), exclusivo de admins.
 *
 * Lista as ações sensíveis da operação com três recortes:
 * - **Geral**: fila das últimas 50 ações (retidas por 60 dias).
 * - **Sensíveis**: ações críticas isoladas (pagamento, encerramento, etc.).
 * - **Por aluno**: busca o histórico de um `id_matricula` específico.
 *
 * Consome `/auditoria` e `/auditoria/aluno/{id}`.
 */
@Component({
  selector: 'app-auditoria-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './auditoria-panel.component.html',
})
export class AuditoriaPanelComponent implements OnInit {
  eventos: EventoAuditoria[] = [];
  carregando = false;

  // Filtro ativo: 'geral' | 'sensivel' | 'aluno'.
  filtro: 'geral' | 'sensivel' | 'aluno' = 'geral';
  buscaAluno = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.carregar();
  }

  selecionar(filtro: 'geral' | 'sensivel' | 'aluno'): void {
    this.filtro = filtro;
    if (filtro !== 'aluno') {
      this.carregar();
    }
  }

  carregar(): void {
    this.carregando = true;
    const url =
      this.filtro === 'aluno'
        ? `/auditoria/aluno/${encodeURIComponent(this.buscaAluno.trim())}`
        : `/auditoria?categoria=${this.filtro}`;
    this.api.get<EventoAuditoria[]>(url).subscribe({
      next: (dados) => {
        this.eventos = dados || [];
        this.carregando = false;
      },
      error: () => {
        this.eventos = [];
        this.carregando = false;
      },
    });
  }

  buscarPorAluno(): void {
    if (!this.buscaAluno.trim()) {
      return;
    }
    this.filtro = 'aluno';
    this.carregar();
  }

  rotuloAcao(acao: string): string {
    const mapa: { [k: string]: string } = {
      editar_contrato: 'Editou contrato',
      destrancar_aluno: 'Destrancou aluno',
      alterar_status: 'Alterou status',
      desativar_aluno: 'Suspendeu aluno',
      receber_pagamento: 'Recebeu pagamento',
      abonar_falta: 'Abonou falta',
      salvar_anamnese: 'Atualizou anamnese',
      encerrar_matricula: 'Encerrou matrícula',
      revogar_encerramento: 'Revogou encerramento',
      expurgo_aluno: 'Expurgou registro',
    };
    return mapa[acao] || acao;
  }
}
