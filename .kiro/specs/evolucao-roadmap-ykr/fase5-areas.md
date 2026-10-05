# Spec — Fase 5: Áreas (Aluno, Professor e Material Didático)

> **Status:** conceito. Última grande fase antes do app multiplataforma
> (Android / iOS / Desktop). Depende das fases 1–4 (todas implementadas) e
> introduz os **papéis de acesso** que o app vai consumir.

## Introdução

Até a Fase 4, o SGI-YKR é um sistema **de retaguarda**: só a diretoria (`admin`)
entra. A Fase 5 abre o sistema para **dois novos públicos** — o **aluno** e o
**professor** — e cria a **Área de Material Didático**, um repositório de
conteúdo cujo consumo é rastreado (abrir, ler, tempo de leitura) e alimenta a
**Auditoria** (Pilar 4).

É também o **pré-requisito funcional do app multiplataforma**: o app será,
essencialmente, o cliente das Áreas do Aluno e do Professor sobre a mesma API
OAuth2 já existente. Por isso a Fase 5 é fronteira: fecha o produto web e abre o
produto mobile.

### Alinhamento com o que já existe

- **Autenticação por papéis já está pronta** no núcleo: o JWT carrega `role` e
  `business/auth.requer_papel(*roles)` protege rotas. Hoje só existe `admin`;
  a Fase 5 ativa `aluno` e `professor` (e o `sensei` já previsto).
- **Auditoria já aceita eventos arbitrários** (`business.auditoria.registrar`):
  os eventos de consumo de material entram por ali, sem novo subsistema de log.
- **Aluno e turmas já são entidades** (`Aluno`, `Turma`, `TurmaMatricula`): a
  Área do Professor e a do Aluno se apoiam nelas.

---

## Escopo das três áreas

### Área do Aluno
Acesso do próprio aluno aos seus dados (somente leitura do que lhe diz respeito)
e ao material liberado para ele.
- Vê: suas turmas, seu calendário de aulas, sua progressão de graduação, sua
  conta corrente (valores em aberto / crédito) e seus próprios registros de
  presença.
- **Não** vê: dados de outros alunos, telas de secretaria, auditoria.
- Consome **material didático** liberado para suas turmas/graduação.

### Área do Professor (Sensei)
Espaço do instrutor, mais amplo que o do aluno, mais restrito que o do admin.
- Vê e opera o **Ambiente Tatame** das suas turmas (presença, cronômetro,
  diário do Sensei) — reaproveitando o que já existe.
- Vê a ficha pedagógica e o **card de alerta crítico** (anamnese) dos alunos das
  suas turmas — informação de segurança que o professor precisa em aula.
- **Não** vê: financeiro, auditoria, encerramento de matrícula (continuam
  exclusivos do admin).
- Publica/organiza **material didático** para suas turmas (se autorizado).

### Área de Material Didático
Repositório de conteúdo (vídeos, PDFs, textos, imagens) organizado por
turma/graduação, com controle de visibilidade e **rastreio de consumo**.
- Cada item tem: título, tipo, conteúdo (link/arquivo), público-alvo (turma e/ou
  faixa de graduação) e autor.
- Toda interação relevante gera um **evento de consumo**: `abriu`, `marcou_lido`,
  `tempo_leitura`. Esses eventos alimentam a Auditoria (Pilar 4) e, no futuro,
  um painel de engajamento.

---

## Conceitos / Modelo de dados (proposto)

- **`Usuario` ganha vínculo opcional com `Aluno`** (um login de aluno aponta
  para seu `id_matricula`) e, para professor, com as turmas que leciona.
- **`Turma` ganha um professor responsável** (`id_professor` → `Usuario`), para
  recortar o que o professor vê.
- **`MaterialDidatico`**: `id`, `titulo`, `tipo` (`video|pdf|texto|imagem`),
  `url_ou_corpo`, `id_turma` (opcional), `graduacao_alvo` (opcional), `autor`,
  `publicado` (bool), `criado_em`.
- **`ConsumoMaterial`**: `id`, `id_material`, `id_aluno`, `evento`
  (`abriu|marcou_lido`), `segundos_leitura` (opcional), `criado_em`. Também
  espelhado como evento de auditoria (categoria própria, p.ex. `material`).

> Papéis novos: `aluno`, `professor` (e `sensei` como alias/−caso de professor
> restrito ao Tatame). O `requer_papel` já suporta múltiplos papéis por rota.

---

## Requisitos (EARS)

### Requisito 5.1 — Autenticação multi-papel

**História:** Como escola, quero que aluno e professor tenham login próprio, para
acessarem suas áreas sem ver dados de terceiros.

#### Critérios de aceitação
1. O SISTEMA DEVE permitir criar usuários com papel `aluno` ou `professor`,
   vinculando o `aluno` ao seu `id_matricula`.
2. QUANDO um usuário `aluno` autentica, O SISTEMA DEVE restringir o acesso aos
   **seus próprios** dados.
3. QUANDO um usuário `professor` autentica, O SISTEMA DEVE restringir o acesso às
   **suas turmas** e aos alunos dessas turmas.
4. As rotas de `admin` (financeiro, auditoria, encerramento) DEVEM continuar
   **inacessíveis** a `aluno`/`professor` (403).

### Requisito 5.2 — Área do Aluno (somente leitura dos próprios dados)

**História:** Como aluno, quero ver minha progressão, meu calendário e minha
situação financeira, para acompanhar meu treino.

#### Critérios de aceitação
1. O SISTEMA DEVE expor ao aluno: suas turmas, seu calendário, sua progressão
   (meses faltantes), sua conta corrente (em aberto / crédito) e suas presenças.
2. O SISTEMA NÃO DEVE permitir ao aluno alterar dados de contrato, status ou de
   outros alunos.
3. O aluno DEVE ver apenas o **material didático** liberado para suas turmas ou
   sua graduação.

### Requisito 5.3 — Área do Professor

**História:** Como professor, quero operar o tatame das minhas turmas e ver os
alertas de saúde dos meus alunos, para dar aula com segurança.

#### Critérios de aceitação
1. O SISTEMA DEVE permitir ao professor operar o **Ambiente Tatame** (presença,
   cronômetro, diário) **somente** das turmas que leciona.
2. O SISTEMA DEVE exibir ao professor o **card de alerta crítico** (anamnese) dos
   alunos das suas turmas.
3. O SISTEMA NÃO DEVE expor ao professor o financeiro, a auditoria nem o
   encerramento de matrícula.

### Requisito 5.4 — Material didático e visibilidade

**História:** Como escola, quero publicar material por turma/graduação, para que
cada aluno veja só o que lhe cabe.

#### Critérios de aceitação
1. O SISTEMA DEVE permitir cadastrar material com público-alvo por **turma** e/ou
   **faixa de graduação**.
2. O SISTEMA DEVE listar a um aluno apenas os materiais cujo público-alvo o
   inclui e que estejam `publicado`.
3. O SISTEMA DEVE permitir que o professor publique material para suas turmas, se
   autorizado.

### Requisito 5.5 — Rastreio de consumo e integração com Auditoria

**História:** Como gestor, quero saber quem abriu/leu cada material e por quanto
tempo, para medir engajamento e manter o histórico de segurança.

#### Critérios de aceitação
1. QUANDO um aluno abre um material, O SISTEMA DEVE registrar um evento `abriu`.
2. QUANDO um aluno marca como lido ou fecha o material, O SISTEMA DEVE registrar
   `marcou_lido` e, quando disponível, o `segundos_leitura`.
3. Os eventos de consumo DEVEM alimentar a **Auditoria** (Pilar 4), numa
   categoria própria (`material`), respeitando as políticas de retenção.

### Requisito 5.6 — Fundação para o app multiplataforma

**História:** Como produto, quero que as Áreas do Aluno e do Professor sejam
servidas pela mesma API, para que o app (Android/iOS/Desktop) seja só mais um
cliente.

#### Critérios de aceitação
1. Todas as funções das Áreas DEVEM ser expostas via **API REST** autenticada por
   OAuth2/JWT (sem lógica exclusiva do front web).
2. O SISTEMA DEVE evitar acoplamento ao Angular: as regras ficam no back-end;
   o app consome os mesmos endpoints da SPA.
3. (Não funcional) Considerar **refresh tokens** e **rate limiting** no login
   antes da distribuição do app.

---

## Faseamento sugerido da implementação

Mesma disciplina das fases anteriores (banco → API → front, com testes a cada
etapa):

- **5a — Papéis e vínculo de usuário:** `aluno`/`professor` no `Usuario`, vínculo
  `Usuario↔Aluno` e `Turma.id_professor`; `requer_papel` nas rotas; testes de
  autorização (403 cruzado).
- **5b — Área do Aluno (leitura):** endpoints "meus dados" (progresso, conta,
  calendário, presenças) filtrados pelo token; tela/app.
- **5c — Área do Professor:** recorte de turmas no Ambiente Tatame + card de
  alerta dos seus alunos.
- **5d — Material Didático:** `MaterialDidatico` + visibilidade; CRUD do admin/
  professor; listagem filtrada do aluno.
- **5e — Consumo + Auditoria:** `ConsumoMaterial` e eventos na auditoria
  (categoria `material`); base para painel de engajamento.

## Riscos e decisões em aberto

- **Armazenamento de arquivos:** material pode ser link externo (simples) ou
  upload (exige storage — disco/S3). Decisão pendente; começar por **link
  externo** reduz escopo.
- **Granularidade de visibilidade:** por turma, por graduação, ou ambos — definir
  com a direção.
- **LGPD do consumo:** o rastreio de leitura é dado comportamental de menores em
  alguns casos; alinhar retenção/anonimização com a política já adotada na
  Auditoria (60 dias).
- **`sensei` × `professor`:** decidir se são o mesmo papel ou se `sensei` é um
  professor com acesso só ao Tatame.
