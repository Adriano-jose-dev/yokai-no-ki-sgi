import { Component, EventEmitter, Output, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

export interface AlunoForm {
  nome: string; whatsapp: string; email: string; data_nascimento?: string;
  idade: number | null;
  endereco?: string; nacionalidade?: string; naturalidade?: string; nome_pai?: string; nome_mae?: string;
  contato_emergencia_nome?: string; contato_emergencia_parentesco?: string; contato_emergencia_telefone?: string;
  trilha_marcial?: 'dojo' | 'legado' | ''; respostas_medicas: { [chave: string]: string };
  detalhamento_medico?: string; termo_imagem?: 'concordo' | 'nao_concordo' | ''; historico_marcial?: string;
  equipamento_proprio: boolean; termo_risco_assinado: boolean; taxa_admissao?: 'padrao' | 'shokubai' | '';
  plano: string; valor_base_contrato: number; acordo_contratual?: string;
  dia_vencimento: number;
}

@Component({
  selector: 'app-matricula-form',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './matricula-form.component.html',
})
export class MatriculaFormComponent implements OnChanges {
  tipoCadastro: 'experimental' | 'completa' = 'experimental';
  abaAtiva = 1;
  acordoEditavel = true;

  @Output() matriculaConcluida = new EventEmitter<void>();
  @Input() alunoParaUpgrade: any = null;

  constructor(private api: ApiService) { }

  perguntasMedicas = [
    { chave: 'problemas_cardiacos', label: 'Possui problemas cardíacos?' }, { chave: 'dores_peito', label: 'Sente dores no peito com frequência?' }, { chave: 'falta_ar', label: 'Sente falta de ar com facilidade?' }, { chave: 'tontura', label: 'Sofre com tonturas ou desmaios?' }, { chave: 'pressao_alta', label: 'Possui pressão alta (hipertensão)?' }, { chave: 'diabetes', label: 'Possui diabetes?' }, { chave: 'asma', label: 'Possui asma ou outro problema respiratório?' }, { chave: 'cirurgias', label: 'Realizou cirurgias nos últimos 12 meses?' }, { chave: 'alergias', label: 'Possui alguma alergia relevante?' },
  ];

  aluno: AlunoForm = {
    nome: '', whatsapp: '', email: '', data_nascimento: '', idade: null, endereco: '', nacionalidade: 'Brasileira', naturalidade: '', nome_pai: '', nome_mae: '',
    contato_emergencia_nome: '', contato_emergencia_parentesco: '', contato_emergencia_telefone: '', trilha_marcial: 'dojo',
    respostas_medicas: this.criarRespostasMedicasVazias(), detalhamento_medico: '', termo_imagem: 'concordo', historico_marcial: '',
    equipamento_proprio: false, termo_risco_assinado: false, taxa_admissao: 'padrao', plano: 'Horas Livres', valor_base_contrato: 20.0, acordo_contratual: '',
    dia_vencimento: 10
  };

  private criarRespostasMedicasVazias() {
    const respostas: { [chave: string]: string } = {};
    this.perguntasMedicas.forEach((pergunta) => respostas[pergunta.chave] = '');
    return respostas;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['alunoParaUpgrade'] && this.alunoParaUpgrade) {
      this.tipoCadastro = 'completa';
      this.aluno.nome = this.alunoParaUpgrade.nome;
      this.aluno.plano = 'Mensalidade';
    }
  }

  get isMenorDeIdade(): boolean {
    return this.aluno.idade !== null && this.aluno.idade !== undefined && this.aluno.idade < 18;
  }

  toggleAba(numero: number): void { this.abaAtiva = this.abaAtiva === numero ? 0 : numero; }
  toggleAcordo(): void { this.acordoEditavel = !this.acordoEditavel; }
  trackByPergunta(index: number, pergunta: any): string { return pergunta.chave; }
  temAlgumaRespostaSim(): boolean { return Object.values(this.aluno.respostas_medicas).some((resposta) => resposta === 'sim'); }

  calcularIdade(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.value) { this.aluno.idade = null; return; }
    const nascimento = new Date(input.value); const hoje = new Date();
    let idade = hoje.getFullYear() - nascimento.getFullYear();
    if (hoje.getMonth() < nascimento.getMonth() || (hoje.getMonth() === nascimento.getMonth() && hoje.getDate() < nascimento.getDate())) idade--;
    this.aluno.idade = idade;
  }

  efetivarMatricula(): void {
    if (!this.aluno.nome) return alert("O nome do aluno é obrigatório.");

    // CORREÇÃO: Aplica a trava de filiação INDEPENDENTE se for experimental ou completa!
    if (this.isMenorDeIdade) {
      if (!this.aluno.nome_pai?.trim() || !this.aluno.nome_mae?.trim()) {
        return alert("O preenchimento do Nome do Pai e da Mãe é OBRIGATÓRIO para alunos menores de idade.");
      }
    }

    let restricaoSerializada = null;
    if (this.tipoCadastro === 'completa' && this.temAlgumaRespostaSim()) {
      const condicoes = Object.keys(this.aluno.respostas_medicas).filter(k => this.aluno.respostas_medicas[k] === 'sim').join(', ');
      if (condicoes) restricaoSerializada = `Condições: ${condicoes}. Obs: ${this.aluno.detalhamento_medico || 'Nenhuma'}`;
    }

    const payload = {
      nome: this.aluno.nome, data_nascimento: this.aluno.data_nascimento || null, whatsapp: this.aluno.whatsapp, email: this.aluno.email, endereco: this.aluno.endereco,
      nacionalidade: this.aluno.nacionalidade, naturalidade: this.aluno.naturalidade, nome_pai: this.aluno.nome_pai, nome_mae: this.aluno.nome_mae,
      contato_emergencia_nome: this.aluno.contato_emergencia_nome, contato_emergencia_parentesco: this.aluno.contato_emergencia_parentesco,
      contato_emergencia_telefone: this.aluno.contato_emergencia_telefone, historico_marcial: this.aluno.historico_marcial,
      equipamento_proprio: this.aluno.equipamento_proprio, termo_risco_assinado: this.aluno.termo_risco_assinado,
      restricao_medica: restricaoSerializada, autorizacao_imagem: this.aluno.termo_imagem === 'concordo',
      modelo_plano: this.aluno.plano, valor_base_contrato: this.aluno.valor_base_contrato, acordo_contratual: this.aluno.acordo_contratual,
      dia_vencimento: this.aluno.dia_vencimento,
      status_atividade: this.tipoCadastro === 'experimental' ? 'Aula Experimental' : 'Ativo',
      inclui_shokubai: this.aluno.taxa_admissao === 'shokubai', taxa_admissao_valor: this.aluno.taxa_admissao === 'shokubai' ? 70.0 : 50.0,
      modo_treino: this.aluno.trilha_marcial === 'legado' ? 'Modo Legado' : 'Modo Dojo'
    };

    const isUpgrade = !!this.alunoParaUpgrade;
    const endpoint = isUpgrade ? `/alunos/${this.alunoParaUpgrade.id_matricula}/upgrade` : '/alunos/matricula';

    this.api.request(isUpgrade ? 'put' : 'post', endpoint, payload).subscribe({
      next: (res: any) => {
        alert(isUpgrade ? `A matrícula experimental foi promovida para Oficial com sucesso!` : `Matrícula efetuada! ID: ${res.id_matricula}`);
        this.matriculaConcluida.emit();
      },
      error: (err) => { alert('Erro ao efetivar matrícula.'); }
    });
  }
}