import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';
import { MatriculaFormComponent } from '../matricula-form/matricula-form.component';
import { ContaCorrentePanelComponent } from '../conta-corrente-panel/conta-corrente-panel.component';

@Component({
  selector: 'app-admin-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule, MatriculaFormComponent, ContaCorrentePanelComponent],
  templateUrl: './admin-detail.component.html'
})
export class AdminDetailComponent implements OnInit {
  aluno: any = null;
  listaAlunos: any[] = [];
  showForm: boolean = false;
  alunoSelecionadoId: string = '';

  exibirModalPagamento: boolean = false;
  valorPagamento: number = 0;
  metodoPagamento: string = 'Pix';
  novaGraduacao: string = '';

  // Modal de confirmação do ENCERRAMENTO definitivo (Hard Delete agendado).
  exibirModalEncerramento: boolean = false;
  encerrando: boolean = false;

  abaAtivaAluno: 'resumo' | 'ficha' | 'financeiro' | 'frequencia' = 'resumo';
  editandoFicha: boolean = false;
  editandoContrato: boolean = false;
  alunoUpgrade: any = null;

  cloneContrato: any = {};
  cloneFicha: any = {};

  novaNotaTitulo: string = '';
  novaNotaPedagogica: string = '';

  listaGraduacoes = [
    'Ashigaru',
    '10º Kyu (Gakusei)', '9º Kyu (Gakusei)', '8º Kyu (Gakusei)', '7º Kyu (Gakusei)', '6º Kyu (Gakusei)',
    '5º Kyu (Gakusei)', '4º Kyu (Gakusei)', '3º Kyu (Gakusei)', '2º Kyu (Gakusei)', '1º Kyu (Gakusei)',
    '1º Dan (Bushi)', '2º Dan (Bushi)', '3º Dan (Bushi)', '4º Dan (Bushi)',
    '5º Dan (Hakushi)', '6º Dan (Denshosha)', '7º Dan (Renshi)', '8º Dan (Kyōshi)', '9º Dan (Hanshi)', '10º Dan (Dōshi)',
    '11º Dan (Shihan)', '12º Dan (Shihan)', '13º Dan (Shihan)', '14º Dan (Shihan)', '15º Dan (Shihan)'
  ];

  perguntasAnamnese = [
    { chave: 'problemas_cardiacos', label: 'Possui problemas cardíacos?' },
    { chave: 'dores_peito', label: 'Sente dores no peito com frequência?' },
    { chave: 'falta_ar', label: 'Sente falta de ar com facilidade?' },
    { chave: 'tontura', label: 'Sofre com tonturas ou desmaios?' },
    { chave: 'pressao_alta', label: 'Possui pressão alta (hipertensão)?' },
    { chave: 'diabetes', label: 'Possui diabetes?' },
    { chave: 'asma', label: 'Possui asma ou outro problema respiratório?' },
    { chave: 'cirurgias', label: 'Realizou cirurgias nos últimos 12 meses?' },
    { chave: 'alergias', label: 'Possui alguma alergia relevante?' }
  ];
  respostasAnamneseEdicao: { [key: string]: string } = {};
  obsMedicaEdicao: string = '';

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.carregarListaAlunos();
    window.addEventListener('abrirNovaMatricula', () => {
      this.alunoUpgrade = null; this.showForm = true; this.alunoSelecionadoId = ''; this.aluno = null;
    });
    window.addEventListener('iniciarUpgrade', (e: any) => {
      this.alunoUpgrade = e.detail; this.showForm = true; this.alunoSelecionadoId = ''; this.aluno = null;
    });
  }

  carregarListaAlunos(): void {
    this.api.get('/alunos').subscribe({
      next: (dados: any) => this.listaAlunos = dados
    });
  }

  carregarDadosAlunoSelect(event: any): void {
    this.alunoSelecionadoId = event.target.value;
    this.carregarDadosAluno(false);
  }

  carregarDadosAluno(manterAba: boolean = false): void {
    if (!this.alunoSelecionadoId) return;
    this.api.get(`/alunos/${this.alunoSelecionadoId}/progresso`).subscribe({
      next: (dados: any) => {
        this.aluno = dados;
        if (!manterAba) this.abaAtivaAluno = 'resumo';
        this.editandoFicha = false;
        this.editandoContrato = false;
        this.novaGraduacao = this.aluno.aluno.graduacao_atual;
        this.parseAnamneseExistente();
      }
    });
  }

  parseAnamneseExistente(): void {
    this.perguntasAnamnese.forEach(p => this.respostasAnamneseEdicao[p.chave] = 'nao');
    this.obsMedicaEdicao = '';
    const texto = this.aluno?.aluno?.restricao_medica;
    if (texto && texto.includes('Condições:')) {
      const partes = texto.split('. Obs: ');
      const condicoes = partes[0].replace('Condições: ', '').split(', ');
      condicoes.forEach((c: string) => { if (c) this.respostasAnamneseEdicao[c] = 'sim'; });
      if (partes[1]) this.obsMedicaEdicao = partes[1];
    } else if (texto) {
      this.obsMedicaEdicao = texto;
    }
  }

  formatarMoeda(valor: number): string {
    return (valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  }

  get totalPendencias(): number {
    return this.aluno?.painel_pendencias?.reduce((acc: number, curr: any) => acc + curr.valor, 0) || 0;
  }

  get notasPedagogicas(): any[] {
    if (!this.aluno?.aluno?.diario_pedagogico) return [];
    try { return JSON.parse(this.aluno.aluno.diario_pedagogico); }
    catch (e) { return []; }
  }

  // INTELIGÊNCIA: Calcula a idade em tempo real baseado no campo de edição
  get isMenorDeIdadeEdicao(): boolean {
    if (!this.aluno) return false;
    const dataBase = this.editandoFicha ? this.cloneFicha.data_nascimento : this.aluno.aluno.data_nascimento;
    if (!dataBase) return false;

    const nascimento = new Date(dataBase);
    const hoje = new Date();
    let idade = hoje.getFullYear() - nascimento.getFullYear();
    if (hoje.getMonth() < nascimento.getMonth() || (hoje.getMonth() === nascimento.getMonth() && hoje.getDate() < nascimento.getDate())) {
      idade--;
    }
    return idade < 18;
  }

  entrarEdicaoContrato(): void {
    this.editandoContrato = true;
    this.cloneContrato = {
      modelo_plano: this.aluno.aluno.modelo_plano,
      valor_contratual_fixo: this.aluno.aluno.valor_contratual_fixo,
      valor_base: this.aluno.aluno.valor_base,
      inclui_shokubai: this.aluno.aluno.inclui_shokubai,
      dia_vencimento: this.aluno.aluno.dia_vencimento || 10,
      observacao_financeira: this.aluno.aluno.observacao_financeira
    };
  }

  salvarEdicaoContrato(): void {
    this.api.put(`/alunos/${this.alunoSelecionadoId}/contrato`, this.cloneContrato).subscribe({
      next: () => {
        alert('Contrato atualizado!');
        this.editandoContrato = false;
        this.carregarDadosAluno(true);
      }
    });
  }

  entrarEdicaoFicha(): void {
    this.editandoFicha = true;
    this.cloneFicha = {
      nome: this.aluno.aluno.nome, data_nascimento: this.aluno.aluno.data_nascimento, graduacao_atual: this.aluno.aluno.graduacao_atual,
      nacionalidade: this.aluno.aluno.nacionalidade, naturalidade: this.aluno.aluno.naturalidade, endereco: this.aluno.aluno.endereco,
      nome_pai: this.aluno.aluno.nome_pai, nome_mae: this.aluno.aluno.nome_mae, whatsapp: this.aluno.aluno.whatsapp, email: this.aluno.aluno.email,
      contato_emergencia_nome: this.aluno.aluno.contato_emergencia_nome, contato_emergencia_parentesco: this.aluno.aluno.contato_emergencia_parentesco, contato_emergencia_telefone: this.aluno.aluno.contato_emergencia_telefone,
      equipamento_proprio: this.aluno.aluno.equipamento_proprio, historico_marcial: this.aluno.aluno.historico_marcial,
      modo_treino: this.aluno.aluno.modo_treino, restricao_medica: this.aluno.aluno.restricao_medica, acordo_contratual: this.aluno.aluno.acordo_contratual
    };
    this.parseAnamneseExistente();
  }

  salvarEdicaoFicha(): void {
    // Agora o sistema verifica a inteligência em tempo real
    if (this.isMenorDeIdadeEdicao) {
      if (!this.cloneFicha.nome_pai?.trim() || !this.cloneFicha.nome_mae?.trim()) {
        return alert("🔒 ERRO JURÍDICO: Aluno menor de idade! O preenchimento do Nome do Pai e da Mãe é OBRIGATÓRIO.");
      }
    }

    let textoMedico = null;
    const selecionadas = Object.keys(this.respostasAnamneseEdicao).filter(k => this.respostasAnamneseEdicao[k] === 'sim').join(', ');
    if (selecionadas || this.obsMedicaEdicao.trim()) {
      textoMedico = `Condições: ${selecionadas}. Obs: ${this.obsMedicaEdicao || 'Nenhuma'}`;
    }
    this.cloneFicha.restricao_medica = textoMedico;

    this.api.put(`/alunos/${this.alunoSelecionadoId}/editar`, this.cloneFicha).subscribe({
      next: () => {
        alert('Ficha cadastral salva!');
        this.editandoFicha = false;
        this.carregarListaAlunos();
        this.carregarDadosAluno(true);
      }
    });
  }

  confirmarPagamento(): void {
    if (this.valorPagamento <= 0) return alert("O valor deve ser maior que zero!");
    const payload = { id_matricula: this.alunoSelecionadoId, valor_pago: this.valorPagamento, metodo: this.metodoPagamento };
    this.api.post('/pagamentos/receber', payload).subscribe({
      next: () => {
        alert(`Baixa efetuada com sucesso!`);
        this.exibirModalPagamento = false; this.valorPagamento = 0;
        this.carregarDadosAluno(true);
      }
    });
  }

  destrancarMatricula(): void {
    if (confirm("Você quer liberar o acesso deste aluno ao tatame e registrar o acordo?")) {
      this.api.put(`/alunos/${this.alunoSelecionadoId}/destrancar`, {}).subscribe({
        next: () => {
          alert("Guerreiro liberado! O acordo foi salvo nas anotações financeiras.");
          this.carregarDadosAluno(true);
        }
      });
    }
  }

  // --- Ciclo de vida da matrícula: Suspensão x Encerramento ---

  /** Suspensão (soft/reversível): mantém o vínculo, tira das telas do dia a dia. */
  suspenderMatricula(): void {
    if (!this.alunoSelecionadoId) return;
    if (!confirm('Suspender este aluno? Ele sai das telas do dia a dia, mas o vínculo e o histórico são mantidos (reversível).')) {
      return;
    }
    this.api.put(`/alunos/${this.alunoSelecionadoId}/desativar`, {}).subscribe({
      next: () => {
        alert('Aluno suspenso. Você pode reativá-lo quando quiser.');
        this.carregarListaAlunos();
        this.aluno = null;
        this.alunoSelecionadoId = '';
      },
      error: () => alert('Não foi possível suspender o aluno.')
    });
  }

  /** Abre o modal de confirmação do encerramento definitivo. */
  abrirModalEncerrar(): void {
    if (!this.alunoSelecionadoId) return;
    this.exibirModalEncerramento = true;
  }

  cancelarEncerramento(): void {
    this.exibirModalEncerramento = false;
  }

  /** Encerramento definitivo: gera o dossiê, agenda o expurgo em 30 dias. */
  confirmarEncerramento(): void {
    if (!this.alunoSelecionadoId || this.encerrando) return;
    this.encerrando = true;
    this.api.post(`/alunos/${this.alunoSelecionadoId}/encerrar`, {}).subscribe({
      next: (res: any) => {
        this.encerrando = false;
        this.exibirModalEncerramento = false;
        alert(
          'Matrícula encerrada. O dossiê foi gerado e ficará disponível na aba ' +
          '"Matrículas encerradas" por 30 dias, quando o registro será removido.'
        );
        this.carregarListaAlunos();
        this.aluno = null;
        this.alunoSelecionadoId = '';
      },
      error: (err) => {
        this.encerrando = false;
        alert(err?.error?.detail || 'Não foi possível encerrar a matrícula.');
      }
    });
  }

  salvarNotaFinanceira(nota: string): void {
    this.api.put(`/alunos/${this.alunoSelecionadoId}/nota-financeira`, { nota }).subscribe({ next: () => alert('Anotação salva!') });
  }

  salvarValorBase(val: number): void {
    this.api.put(`/alunos/${this.alunoSelecionadoId}/valor-base`, { valor_base: val }).subscribe({ next: () => alert('Valor Base modificado!') });
  }

  alterarStatus(e: any): void {
    this.api.put(`/alunos/${this.alunoSelecionadoId}/status`, { novo_status: e.target.value }).subscribe({ next: () => this.carregarDadosAluno(true) });
  }

  promoverAluno(): void {
    this.api.put(`/alunos/${this.alunoSelecionadoId}/promover`, { nova_graduacao: this.novaGraduacao }).subscribe({ next: () => { this.novaGraduacao = ''; this.carregarDadosAluno(true); } });
  }

  toggleHoraFlexivel(): void {
    if (!this.aluno || !this.alunoSelecionadoId) return;
    this.api.put(`/alunos/${this.alunoSelecionadoId}/hora-flexivel`, {}).subscribe({
      next: () => { this.aluno.aluno.hora_flexivel = !this.aluno.aluno.hora_flexivel; }
    });
  }

  salvarDiarioPedagogico(): void {
    if (!this.novaNotaPedagogica.trim() || !this.novaNotaTitulo.trim()) {
      alert("Preencha o Título e a Descrição do Post-it!"); return;
    }
    const list = this.notasPedagogicas;
    const dt = new Date().toLocaleDateString('pt-BR') + ' ' + new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    list.unshift({ data: dt, titulo: this.novaNotaTitulo.trim(), texto: this.novaNotaPedagogica.trim() });
    const str = JSON.stringify(list);
    this.api.put(`/alunos/${this.alunoSelecionadoId}/diario-pedagogico`, { nota: str }).subscribe({
      next: () => { this.aluno.aluno.diario_pedagogico = str; this.novaNotaTitulo = ''; this.novaNotaPedagogica = ''; }
    });
  }
}