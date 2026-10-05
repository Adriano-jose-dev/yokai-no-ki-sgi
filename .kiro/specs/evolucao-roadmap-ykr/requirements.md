# Requisitos — Evolução do SGI-YKR (Roadmap de Produto)

## Introdução

Esta Spec cobre o roadmap de evolução do SGI-YKR definido em reunião de produto
com a direção do Dojo (Adriano e Laynara). São quatro pilares de negócio
profundos, mais um pilar futuro (áreas de material didático / professor / aluno).

A implementação é **por fases, um pilar por vez**, com verificação a cada etapa.
A ordem foi definida por **dependência**: o Financeiro depende de Turma/Calendário
(valor base é da turma; horas do mês vêm do calendário; cancelar aula altera o
valor), então **Turmas vem antes de Financeiro**.

- **Fase 0 — Modularização em domínios** (pré-requisito técnico): reorganizar
  `models.py` e `routers/` em módulos (tatame, financeiro, saúde, auditoria),
  pois os pilares triplicam a complexidade do modelo atual.
- **Fase 1 — Turmas, Modo Tatame e Calendário** (Pilar 1): introduz o conceito
  novo de Turma — base para o financeiro.
- **Fase 2 — Financeiro: conta corrente e automações** (Pilar 3): construído
  sobre as turmas e o calendário. **Conceito já travado** (ver seção).
- **Fase 3 — Prontuário Médico (Anamnese) e card de alerta crítico** (Pilar 2).
- **Fase 4 — Auditoria (log de segurança)** (Pilar 4): transversal, por último.
- **Fase 5 (futuro) — Áreas: material didático, professor e aluno** (Pilar 5):
  apenas mapeado, não detalhado nesta rodada.

Stack mantida: Python/FastAPI/SQLAlchemy/Alembic no back-end; Angular 17 +
TailwindCSS (paleta sumi/carmesim/ouro) + Lucide no front-end. O steering
`regras-negocio-ykr.md` é a fonte da verdade e será atualizado a cada fase.

> **Status desta Spec:** o **Pilar 1 (Turmas/Calendário)** está em refinamento
> conceitual (próximo a implementar). O **Pilar 3 (Financeiro)** teve o conceito
> **travado** e aguarda a Turma como base. Os demais pilares estão registrados
> como captura fiel do que foi debatido — ainda **não** são decisões técnicas
> fechadas.

---

## Fase 2 — Pilar 3: Financeiro (Conta Corrente e Automações)

> **Conceito travado** (reunião de produto). Depende da Fase 1 (Turmas e
> Calendário) estar implementada, pois o valor nasce da turma e do calendário.

**Objetivo:** transformar o financeiro do aluno em uma **conta corrente**
(débito × crédito), com a mensalidade calculada automaticamente a partir do
calendário e um recurso de abono de falta.

### Conceitos de valor (três níveis)

- **Valor base:** valor da hora-aula de uma **turma específica**.
- **Valor por aula** (Hora-Aula): `valor_base × horas da aula`.
- **Valor mensalidade** (mensalistas): `valor_base × horas de aula no mês`,
  usando o **número real de ocorrências do mês** conforme o **calendário** (não
  uma média fixa). Baseia-se nos **dias de aula** (não só nas horas), para
  refletir o tempo investido do professor.

### Regra da mensalidade (acumulado por calendário, não pacote fixo)

- No início do mês, o sistema **gera o valor** da mensalidade somando as horas
  de todas as aulas previstas no **calendário** daquele mês para a(s) turma(s)
  do aluno.
- Esse valor **só muda** se **o professor/escola cancelar uma aula** — a aula
  cancelada sai da conta e o valor diminui. **Falta do aluno NÃO altera o
  valor.**
- No **dia do vencimento** (ex.: dia 15), o valor gerado vira **débito** na conta
  corrente.
- A **trava de inadimplência** existente (vencimento + 5 dias) continua válida
  sobre esse débito.
- Interpretação-chave: o mensalista paga pelas aulas que a **escola ofertou** no
  mês, não pelas que ele compareceu.

### Regras de conta corrente

- O **débito** só passa a existir quando a aula/mensalidade é **gerada** (aula de
  hora-aula realizada e não paga; ou mensalidade no vencimento).
- Valor pago a mais fica guardado como **crédito** (saldo positivo).
- O crédito **abate débito** no momento em que o débito é gerado. Fora disso, o
  valor permanece como crédito.
- A **taxa de admissão (matrícula)** continua existindo **sem alteração** — é
  mais um débito, quitável pelo crédito.

### Abono de falta

- Aplica-se **somente a mensalistas**.
- É puramente sobre **presença/penalidade por falta** — permite que o aluno
  falte de forma justificada sem penalidade.
- **NÃO altera o valor da mensalidade.** A única coisa que reduz o valor é o
  **cancelamento de aula pela escola**.

### Requisito 2.1 — Três níveis de valor

**História:** Como gestor, quero distinguir valor base, valor por aula e valor
mensalidade, para cobrar corretamente conforme o tipo de turma.

#### Critérios de Aceitação

1. O SISTEMA DEVE associar um **valor base** (valor da hora) a cada turma.
2. QUANDO uma aula de hora-aula é encerrada, O SISTEMA DEVE calcular o valor por
   aula como `valor_base × horas_da_aula`.
3. PARA mensalistas, O SISTEMA DEVE calcular a mensalidade como `valor_base ×
   horas **previstas** das ocorrências do mês no calendário` da(s) turma(s) do
   aluno. O cronômetro global do Modo Tatame é **validação do professor** e
   **não** entra neste cálculo — apenas aulas `canceladas` reduzem o valor.

### Requisito 2.2 — Geração da mensalidade e vencimento

**História:** Como gestor, quero que a mensalidade seja gerada do calendário e
só vire débito no vencimento, para refletir as aulas realmente ofertadas.

#### Critérios de Aceitação

1. NO início do mês, O SISTEMA DEVE calcular o valor da mensalidade a partir das
   ocorrências previstas no calendário.
2. SE a escola cancelar uma aula do mês, ENTÃO O SISTEMA DEVE recalcular o valor,
   removendo as horas da aula cancelada.
3. NO dia de vencimento, O SISTEMA DEVE converter o valor em **débito**.
4. Faltas do aluno NÃO DEVEM alterar o valor da mensalidade.

### Requisito 2.3 — Conta corrente (débito e crédito)

**História:** Como gestor, quero ver o saldo do aluno como conta corrente
(valores em aberto e crédito), para gerir pagamentos antecipados e pendências.

#### Critérios de Aceitação

1. O SISTEMA DEVE manter um **saldo de crédito** por aluno (valor pago a mais).
2. O débito SÓ DEVE ser criado quando a aula/mensalidade é gerada e não paga.
3. QUANDO um débito é gerado, O SISTEMA DEVE abatê-lo do crédito disponível, se
   houver.
4. O SISTEMA DEVE exibir no perfil do aluno "Valores em Aberto" (débito) e
   "Caixa/Crédito" (saldo positivo).

### Requisito 2.4 — Abono de falta (mensalistas)

**História:** Como admin, quero abonar faltas justificadas de mensalistas, para
que o aluno não leve penalidade por ausência — sem alterar o valor do mês.

#### Critérios de Aceitação

1. O SISTEMA DEVE permitir abono de falta **apenas** para mensalistas.
2. O abono DEVE registrar justificativa e autor (admin).
3. O abono NÃO DEVE alterar o valor da mensalidade (atua só sobre presença).

---

## Fase 1 — Pilar 1: Turmas, Modo Tatame e Calendário

> **Fase atual em refinamento.** É a base para o Financeiro (Fase 2).

**Objetivo:** introduzir o conceito de **Turma** e um Modo Tatame orientado a
turma/data/hora, com calendário de ocorrências editável e dois modos de
cronômetro.

### Conceito de Turma

Campos de uma turma:
- **Nome** (ex.: Tengu, Kirin, Rio Bossa Nova, No Mori, Unity 60+ Korei-bu,
  Unity Seinen-Bu, Unity Shonen-Bu).
- **Tipo de pagamento:** `Mensalidade`, `Fixo` ou `Hora-Aula`.
- **Dias/horários** (recorrência: ex. "todo sábado 19h–21h", "primeira e
  terceira terça-feira do mês").
- **Classe:** `Dojo` ou `Legado`.
- **Lista de alunos matriculados.**

Regras:
- Um aluno **pode estar em mais de uma turma**. Alunos de **Legado** podem
  participar de aulas de **Dojo gratuitamente** (alunos "ocorrentes"/opcionais).

### Modo Tatame por tipo de turma

- O visual deve **reaproveitar o design da aba de Presença** atual.
- Ao entrar no Modo Tatame no dia da aula, o sistema pergunta: **nome da turma,
  classe, tipo de pagamento** (define cronômetro e layout) e permite **adicionar
  os alunos** desejados (incluindo ocorrentes/opcionais).
- **Turma Mensalidade:** cronômetro **global** da aula (no canto da tela). O card
  de cada aluno mantém o formato atual, mas **no lugar do cronômetro** há um
  **botão Presença/Ausência** e o **diário do Sensei**.
- **Turma Hora-Aula:** cronômetro **individual** em cada card (como hoje). Ao
  parar o tempo do aluno, um **pop-up confirma presença e o tempo exato**. Cobra
  como hoje.

### Calendário e Ocorrências

- Ao criar uma turma com **recorrência**, o sistema **gera automaticamente as
  ocorrências de aula** do período. O admin tem **autonomia total** para editar,
  excluir, mover ou adicionar aulas avulsas.
- A **recorrência suporta qualquer regra** (dia(s) da semana fixos — Unity/No
  Mori aos sábados; ocorrência do mês — Kirin na 1ª e 3ª terça; etc.).
  Tecnicamente será modelada por um padrão de recorrência flexível (ex.: RRULE).
- Uma **Ocorrência (Aula)** = uma turma numa data específica, com estado:
  `prevista`, `realizada` ou `cancelada`. Para mensalistas, só há `prevista`,
  `realizada` ou `cancelada` (sem remarcação — remarcação é conceito de
  Hora-Aula).
- **Adições** de aula ocorrem no ambiente **Tatame**; **modificações** (ver,
  editar, excluir) ocorrem no ambiente **Calendário**.
- Dias de aula e eventos aparecem com **bolinhas coloridas** (por tipo/estado);
  clicar no dia mostra o histórico de **quem participou e quanto tempo durou**.

### Entrada no Tatame (reuso da ocorrência prevista)

- No dia da aula, ao entrar no Tatame, o sistema **localiza a ocorrência
  prevista** daquele dia e abre o fluxo **pré-preenchido** (turma, classe, tipo
  de pagamento, alunos).
- As perguntas (nome da turma, classe, tipo, alunos) servem para **confirmar ou
  editar**:
  - Se o admin **apenas confirma** → segue a ocorrência já programada (sem
    duplicar).
  - Se o admin **altera** algo → o sistema gera uma **aula nova/modificada**
    para aquele dia.
- Para uma aula **avulsa** (sem ocorrência prevista), o fluxo cria a ocorrência
  do zero.

### Requisito 1.1 — Cadastro de Turma

**História:** Como gestor, quero cadastrar turmas com tipo, recorrência e classe,
para organizar as aulas e servir de base ao financeiro.

#### Critérios de Aceitação

1. O SISTEMA DEVE permitir criar uma turma com: nome, tipo de pagamento
   (`Mensalidade` ou `Hora-Aula`), regra de recorrência, classe (`Dojo`/`Legado`)
   e um **valor base** (valor da hora da turma).
2. O SISTEMA DEVE permitir associar alunos a uma turma como **matriculados** ou
   **ocorrentes**.
3. A classe `Dojo`/`Legado` é um controle organizacional; sua única regra
   funcional é permitir que um aluno **Legado assista aulas de Dojo
   gratuitamente** (como ocorrente).

### Requisito 1.2 — Relação aluno↔turma (matriculado × ocorrente)

**História:** Como gestor, quero que um aluno tenha uma turma de matrícula e
possa ser ocorrente em outras, para refletir o caso Legado→Dojo.

#### Critérios de Aceitação

1. Um aluno DEVE ter **uma turma de matrícula** (onde é cobrado) e PODE ser
   **ocorrente** em outras turmas.
2. A participação como **ocorrente** de um Legado em turma de Dojo NÃO DEVE gerar
   cobrança.

### Requisito 1.3 — Geração e edição de ocorrências

**História:** Como gestor, quero que as ocorrências sejam geradas da recorrência
e totalmente editáveis, para controlar o calendário real do dojo.

#### Critérios de Aceitação

1. QUANDO uma turma com recorrência é criada, O SISTEMA DEVE gerar as ocorrências
   do período.
2. O SISTEMA DEVE permitir **editar, excluir, mover e adicionar** ocorrências.
3. QUANDO a escola cancela uma ocorrência de mensalidade, O SISTEMA DEVE marcá-la
   como `cancelada` (impacto no financeiro — ver Fase 2).

### Requisito 1.4 — Modo Tatame por tipo de turma

**História:** Como instrutor, quero que o Modo Tatame se ajuste ao tipo da turma,
para operar a aula corretamente.

#### Critérios de Aceitação

1. O layout do Modo Tatame DEVE reaproveitar o design da aba de **Presença**.
2. PARA turma `Mensalidade`: o cronômetro é **global** (canto da tela, controle
   do professor / validação da duração da aula — **não entra no cálculo
   financeiro**); cada card de aluno tem **botão Presença/Ausência** e o
   **diário do Sensei** (no lugar do cronômetro individual).
3. PARA turma `Hora-Aula`: o cronômetro é **individual** no card (como hoje); ao
   parar, um pop-up confirma **presença e tempo exato**; a cobrança segue o
   comportamento atual (`valor_base × horas`).

### Requisito 1.5 — Histórico por dia no calendário

**História:** Como gestor, quero clicar num dia e ver quem participou e por
quanto tempo, para auditar a frequência.

#### Critérios de Aceitação

1. O calendário DEVE exibir dias com aula/evento com marcadores coloridos.
2. AO clicar num dia, O SISTEMA DEVE listar participantes e a duração da aula.

---

## Fase 3 — Pilar 2: Prontuário Médico (Anamnese) e Card de Alerta Crítico

**Objetivo:** anamnese versionada com validade e um card de alerta de emergência
extraído dela.

### Regras

- A ficha de anamnese completa é **refeita a cada 6 ou 12 meses**.
- O sistema deve **alertar** quando a anamnese vence.
- As anamneses anteriores **não somem** — viram **histórico** (versões).
- **Card de alerta crítico:** área de destaque no perfil do aluno (estilo
  post-it/alerta) com informações críticas que **interferem diretamente na
  aula** — ex.: asma, condição cardíaca ("ritmo cardíaco"), ossos frágeis,
  problemas de articulação, condições mentais (ex.: autismo suporte nível 3),
  contatos de emergência.
- O card é **extraído da anamnese**: o aluno preenche, e o sistema (ou uma IA)
  analisa e gera o card de alerta crítico.

---

## Fase 4 — Pilar 4: Auditoria (Log de Segurança)

**Objetivo:** aba exclusiva de administradores com histórico de ações sensíveis,
com filtros e políticas de retenção.

### Regras

- Aba de auditoria exclusiva para **Administradores**.
- Registra ações como: quem editou, quem apagou um pagamento, etc.
- **Filtros/categorias de auditoria:**
  - **Geral:** limite de **50 ações** (fila — ao exceder, remove a mais antiga);
    as demais são guardadas por **60 dias**.
  - **Aluno:** histórico por aluno.
  - **Sensíveis:** ações críticas isoladas.
- **Retenção de 60 dias** também para a anamnese dentro da auditoria.
- Futuro: rastrear consumo de **material didático** (abriu, marcou como lido,
  tempo de leitura) — depende do Pilar 5.

---

## Fase 5 (Futuro — apenas mapeado) — Áreas: Material Didático, Professor e Aluno

**Objetivo (não detalhado nesta rodada):** criar três áreas novas:
- **Área do Aluno:** acesso do aluno aos próprios dados/material.
- **Área do Material Didático:** repositório de conteúdo (gera eventos de
  consumo para a auditoria: abertura, leitura, tempo de leitura).
- **Área do Professor:** espaço do instrutor.

Este pilar fica **registrado como futuro** e será detalhado quando priorizado.
A auditoria do consumo de material (Pilar 4) depende deste pilar.
