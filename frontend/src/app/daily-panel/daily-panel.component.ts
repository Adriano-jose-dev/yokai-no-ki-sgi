import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LucideAngularModule } from 'lucide-angular';

import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-daily-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  templateUrl: './daily-panel.component.html'
})
export class DailyPanelComponent implements OnInit, OnDestroy {
  alunos: any[] = [];
  sessoesAtivas: { [id: string]: boolean } = {};
  diarios: { [id: string]: string } = {};
  descontos: { [id: string]: number } = {};
  temposIniciais: { [id: string]: number } = {};
  temposAtuais: { [id: string]: number } = {};
  intervalId: any;
  limiteExperimental: number = 0.0166;

  pesosGraduacao: { [key: string]: number } = {
    'Ashigaru': 1, '10º Kyu': 2, '9º Kyu': 3, '8º Kyu': 4, '7º Kyu': 5,
    '6º Kyu': 6, '5º Kyu': 7, '4º Kyu': 8, '3º Kyu': 9, '2º Kyu': 10,
    '1º Kyu': 11, '1º Dan': 12, '2º Dan': 13, '3º Dan': 14, '4º Dan': 15, '5º Dan': 16
  };

  constructor(private api: ApiService) { }

  ngOnInit(): void {
    this.carregarAlunos();
    this.intervalId = setInterval(() => this.atualizarCronometros(), 1000);
  }
  ngOnDestroy(): void { if (this.intervalId) clearInterval(this.intervalId); }

  carregarAlunos(): void {
    this.api.get('/tatame/ativos').subscribe({
      next: (dados: any) => {
        this.alunos = dados;
        this.alunos.forEach(a => {
          if (a.hora_entrada) {
            this.sessoesAtivas[a.id_matricula] = true;
            this.temposIniciais[a.id_matricula] = new Date(a.hora_entrada).getTime();
            this.temposAtuais[a.id_matricula] = Date.now();
            if (this.descontos[a.id_matricula] === undefined) this.descontos[a.id_matricula] = 0;
          } else {
            this.sessoesAtivas[a.id_matricula] = false;
          }
        });
        this.ordenarFilaTatame();
      },
      error: (err) => console.error('Erro ao carregar tatame:', err)
    });
  }

  ordenarFilaTatame(): void {
    this.alunos.sort((a, b) => {
      const ativoA = this.sessoesAtivas[a.id_matricula];
      const ativoB = this.sessoesAtivas[b.id_matricula];
      if (ativoA && !ativoB) return -1;
      if (!ativoA && ativoB) return 1;
      if (ativoA && ativoB) return (this.temposIniciais[a.id_matricula] || 0) - (this.temposIniciais[b.id_matricula] || 0);
      const gradA = this.pesosGraduacao[a.graduacao_atual] || 0;
      const gradB = this.pesosGraduacao[b.graduacao_atual] || 0;
      if (gradA !== gradB) return gradB - gradA;
      return a.nome.localeCompare(b.nome);
    });
  }

  atualizarCronometros(): void {
    const agora = Date.now();
    for (const id in this.sessoesAtivas) {
      if (this.sessoesAtivas[id]) this.temposAtuais[id] = agora;
    }
  }

  getTempoDecorrido(id: string): string {
    if (!this.sessoesAtivas[id] || !this.temposIniciais[id]) return '00:00:00';
    const diff = this.temposAtuais[id] - this.temposIniciais[id];
    const horas = Math.floor(diff / 3600000);
    const minutos = Math.floor((diff % 3600000) / 60000);
    const segundos = Math.floor((diff % 60000) / 1000);
    return `${horas.toString().padStart(2, '0')}:${minutos.toString().padStart(2, '0')}:${segundos.toString().padStart(2, '0')}`;
  }

  atingiuCota(aluno: any): boolean {
    return aluno.status_atividade === 'Aula Experimental' && aluno.total_horas_exp >= this.limiteExperimental;
  }

  // Modificado: Passa o aluno pro evento de Upgrade
  avisoMatricular(aluno: any): void {
    alert(`🔒 Cota de Aula Experimental atingida!\n\nVocê será redirecionado para a Secretaria para efetivar a matrícula do guerreiro ${aluno.nome}.`);
    window.dispatchEvent(new CustomEvent('navegarParaSecretaria'));
    setTimeout(() => { window.dispatchEvent(new CustomEvent('iniciarUpgrade', { detail: aluno })); }, 100);
  }

  startTreino(idMatricula: string): void {
    this.api.post('/sessao/start', { id_matricula: idMatricula }).subscribe({
      next: () => this.carregarAlunos(),
      error: (err) => alert('Falha ao iniciar o cronômetro.')
    });
  }

  stopTreino(idMatricula: string): void {
    const payload = { id_matricula: idMatricula, diario_sensei: this.diarios[idMatricula] || null, desconto_aplicado: this.descontos[idMatricula] || 0.0 };
    this.api.post('/sessao/stop', payload).subscribe({
      next: (res: any) => {
        const alunoFechado = this.alunos.find(a => a.id_matricula === idMatricula);
        if (alunoFechado && alunoFechado.modelo_plano === 'Mensalidade') {
          if (res.valor > 0) {
            alert(`Sessão finalizada!\n⚠️ Limite de 3h diárias ultrapassado!\nValor ADICIONAL gerado: R$ ${res.valor.toFixed(2).replace('.', ',')}`);
          } else {
            alert(`Sessão finalizada!\nPresença registrada com sucesso no diário.`);
          }
        } else {
          alert(`Sessão finalizada!\nValor: R$ ${res.valor.toFixed(2).replace('.', ',')}`);
        }
        this.sessoesAtivas[idMatricula] = false;
        this.diarios[idMatricula] = '';
        this.descontos[idMatricula] = 0;
        this.carregarAlunos();
      },
      error: (err) => alert('Falha ao encerrar a sessão.')
    });
  }
}