# Roadmap / Evolução Futura — SGI-YKR

Este documento registra a visão de produto para além das Fases B (estabilização)
e A (produção), que estão detalhadas em `requirements.md`, `design.md` e
`tasks.md`. As fases aqui descritas são **direcionais**: servem para planejar e
para comunicar a maturidade do projeto no portfólio, e serão convertidas em Specs
próprias (com requisitos e design detalhados) quando forem priorizadas.

**Filosofia mantida:** monólito modularizado e eficiente. Sem microserviços,
Kubernetes ou filas enquanto o porte da escola não justificar. Cada adição deve
ter valor real para a operação do Dojo ou impacto claro de portfólio — de
preferência, os dois.

## Onde estamos

- **Fase B — Estabilização:** correção de regras, unificação da trava, rota de
  valor base, soft delete, environments no front. _(planejada)_
- **Fase A — Produção:** autenticação JWT extensível, CORS restrito, Postgres +
  Alembic, agendador da trava, deploy de baixo custo, Swagger e CI/CD. _(planejada)_

O papel `Sensei` já foi previsto na modelagem de autenticação da Fase A, o que
abre caminho natural para o Portal do Aluno (Fase C).

---

## Fase C — Valor operacional para a escola

Foco em funcionalidades que aliviam a rotina da secretaria e da Sensei Lay e
aumentam a retenção de alunos. Reaproveitam dados e regras que o sistema já
possui.

### C1. Notificações proativas (WhatsApp / e-mail)

- Avisos automáticos de vencimento próximo, atraso e aptidão para exame de faixa.
- Reaproveita o agendador diário (Fase A) e os cálculos de vencimento/juros e de
  progressão já existentes.
- Ponto de atenção: envio de WhatsApp exige provedor (API oficial ou gateway);
  e-mail é mais simples para começar. Avaliar custo e requisitos antes de
  implementar.

### C2. Portal do Aluno (self-service)

- Área autenticada onde o aluno acompanha progresso de faixa, meses faltantes
  para o exame, histórico de treinos e pendências financeiras.
- Introduz um papel `Aluno` no JWT, complementando `admin` e `sensei`.
- Reduz a carga de perguntas na secretaria e engaja o aluno na própria evolução.

### C3. Gestão de exames de graduação

- Fecha o ciclo da régua marcial: agendar exames, registrar banca e notas,
  promover e emitir certificado de faixa.
- Parte do dado já existe (`apto_exame`, `meses_faltantes`); falta o fluxo de
  exame e o registro histórico de graduações.

### C4. Emissão de documentos em PDF

- Recibos de pagamento na baixa, comprovantes e certificados de graduação.
- Profissionaliza a operação e é requisito comum de uma escola real.

---

## Fase D — Diferencial de portfólio (vitrine técnica)

Foco em recursos que destacam o repositório no GitHub, aplicados ao domínio real
do Dojo — não tecnologia por moda.

### D1. Assistente pedagógico com IA

- IA que lê o `diario_sensei` (anotações por sessão) e o `diario_pedagogico`,
  resume a evolução do aluno ao longo do tempo e sugere focos para o próximo
  treino.
- Usa dados que o sistema já coleta. É o diferencial mais forte: IA aplicada a um
  nicho com dados reais, não um CRUD com IA colada por cima.

### D2. Insight de retenção (risco de evasão)

- Sinaliza alunos com risco de sair, cruzando queda de frequência e atrasos
  recorrentes.
- Pode começar baseado em regras simples e evoluir para um modelo conforme os
  dados crescem.

### D3. Dashboard gerencial

- Visão de dono do negócio: faturamento do mês, inadimplência total, projeção de
  receita, horas de tatame vendidas.
- Todos os dados de origem já existem (pagamentos, sessões, contratos); falta a
  camada de agregação e visualização.

---

## O que deliberadamente ficou de fora

- Microserviços, Kubernetes, filas de mensageria e outras arquiteturas de larga
  escala. Para o porte de uma escola de artes marciais, adicionam complexidade
  sem retorno e sinalizam over-engineering em um portfólio.
- Multi-tenant / SaaS para várias escolas: só faria sentido se o objetivo do
  produto mudar de "gestão do nosso Dojo" para "plataforma vendida a terceiros".

## Como priorizar

Sugestão de ordem quando as Fases B e A estiverem concluídas:

1. **C1 (notificações)** — maior alívio imediato na rotina, baixo esforço sobre o
   agendador já pronto.
2. **D1 (assistente pedagógico)** — maior impacto de portfólio, usa dados
   existentes.
3. **C3 (exames)** e **C4 (PDFs)** — fecham o ciclo marcial da escola.
4. **C2 (portal do aluno)** e **D3 (dashboard)** — ampliam alcance e visão
   gerencial.
5. **D2 (retenção)** — evolui conforme o histórico de dados cresce.

Cada item vira uma Spec dedicada no momento da priorização.
