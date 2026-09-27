---
inclusion: always
---

# Diretrizes de Negócio e Arquitetura — SGI-YKR

**Contexto:** Plataforma de gestão para um Dojo de artes marciais tradicionais
(Kenjutsu/Bujutsu) — Yōkai no Ki Ryūha. Toda alteração no código deve respeitar
as regras abaixo.

---

## 1. Módulo Financeiro e Tatame (Core)

### 1.1 Hierarquia de Cobrança por Sessão (Tatame)

Quando uma sessão encerra (`hora_saida`), o tempo entre entrada e saída é
convertido para **horas decimais**. O custo é calculado conforme o plano:

1. **`hora_flexivel == True`:**
   `Custo = Horas Decimais * Valor Base`

2. **Plano `Mensalidade`:** há uma franquia de **3 horas**.
   `Custo = (Horas Decimais - 3.0) * Valor Base`
   Cobra apenas o que exceder 3h. Se `Horas Decimais <= 3.0`, o custo é `0`
   (nunca negativo).

3. **Plano `Intensivão`:**
   `Custo = Horas Decimais * (Valor Base * 1.5)`

4. **Plano `Horas Livres`:**
   `Custo = Horas Decimais * Valor Base`

### 1.2 Trava Automática de Inadimplência

- Aplica-se **apenas** ao plano `Mensalidade`.
- Se a data atual for maior que `dia_vencimento + 5 dias`:
  - O status do aluno muda forçadamente para `Trancado`.
  - A string `[TRAVA AUTOMÁTICA]` é adicionada ao campo `observacao_financeira`.
- Se um aluno for trancado enquanto tem uma sessão de tatame aberta, a sessão
  deve ser encerrada imediatamente (`hora_saida = datetime.now()`).
- Alunos `Trancados` **não aparecem** na tela do Tatame e **não podem** iniciar
  sessões.
- **Momento da avaliação:** hoje (MVP) a trava é avaliada **sob demanda** (lazy
  evaluation), disparada nas rotas de leitura de progresso do aluno e de
  salvamento de edição de contrato. **Evolução planejada para produção:** uma
  background task (ex.: APScheduler) rodando diariamente à meia-noite para
  varrer o banco e aplicar as travas de forma proativa.

### 1.3 Bypass de Acordo (Whitelist)

- Se o campo `observacao_financeira` contiver a string exata `[ACORDO]`, o
  sistema de trava automática **ignora** este aluno (não é bloqueado mesmo em
  atraso).

---

## 2. Matrícula e Secretaria

- **Validação de Menoridade:** Se o aluno for menor de 18 anos (calculado
  dinamicamente no front-end ou validado no back-end), os campos `nome_pai` e
  `nome_mae` são estritamente obrigatórios, independente do tipo de cadastro
  (Experimental ou Completa).
- **Planos e Vencimento:** O campo `dia_vencimento` deve existir **apenas** para
  planos do tipo `Mensalidade`. Ocultar/ignorar para `Horas Livres` ou
  `Intensivão`.
- **Presença Automática:** Todo aluno que tiver uma sessão iniciada e encerrada
  no Módulo Tatame deve receber um registro automático de `Presente` na tabela
  `Presencas`, com a data do dia.

---

## 3. Progressão Marcial (Régua de Graduação)

A meta de tempo de faixa depende do nível atual do aluno:

- **Gakusei** (nome contém `Ashigaru` ou `Kyu`): meta = **5 meses**.
- **Bushi / Dan** (nome contém `Dan`): meta = **12 meses**.

A API de progresso deve **sempre** retornar os meses faltantes para o próximo
exame.

---

## 4. Convenções Técnicas do Projeto

- **Back-end:** Python, FastAPI, SQLAlchemy, SQLite (futura migração para
  PostgreSQL). Respostas em JSON.
- **Front-end:** Angular. Componentização clara. Estilização com TailwindCSS.
- **Política de Deletes:** o comportamento depende do ciclo de vida da
  matrícula (ver seção 5). Em operações do dia a dia (suspensão/pausa), **nunca**
  usar Hard Delete — usar **Soft Delete** (`status_atividade`). O Hard Delete é
  permitido **exclusivamente** pelo fluxo de **Encerramento definitivo** (seção
  5), como expurgo agendado e em conformidade com a LGPD.

---

## 5. Ciclo de Vida da Matrícula: Suspensão × Encerramento

O sistema distingue dois desligamentos, com semânticas e mecanismos diferentes:

### 5.1 Suspensão (Soft Delete — reversível)

- Para alunos que **pausam** o treino mas **mantêm o vínculo** com a escola.
- Muda o `status_atividade` para `Inativo` (ou `Trancado`, no caso da trava de
  inadimplência). O registro **nunca** é removido do banco.
- O aluno some das telas operacionais (Tatame, Presença, lista geral), mas pode
  ser reativado a qualquer momento, preservando todo o histórico.

### 5.2 Encerramento (Hard Delete agendado — definitivo)

Para alunos que **cortam o vínculo** com a escola. Ação restrita ao papel
`admin`. Fluxo:

1. **Dossiê primeiro (a prova vem antes):** gera-se um **PDF completo** com todos
   os dados do aluno (ficha, perfil marcial, contrato, diário, histórico de
   sessões, pagamentos e presenças). Ele é a prova documental que resta após o
   expurgo.
2. **Retenção de 30 dias:** o aluno passa ao status `Encerrado` (sai das telas do
   dia a dia) e entra na aba **Matrículas Encerradas**. Nada é apagado ainda —
   apenas ocultado. O dossiê fica disponível para download nesse período.
3. **Revogação:** durante os 30 dias, qualquer `admin` pode **revogar** o
   encerramento. Como nada foi apagado, a revogação apenas restaura o
   `status_atividade` ao **estado anterior** (registrado no encerramento) e
   remove o registro de encerramento, cancelando o expurgo.
4. **Expurgo (Hard Delete):** ao fim dos 30 dias, um job diário do APScheduler
   elimina definitivamente o registro do aluno. Conformidade com a LGPD: dados
   pessoais não são retidos após o fim do vínculo.

> **Escopo atual do expurgo (provisório):** até a divisão planejada em setores
> (financeiro/secretaria como domínios separados), o expurgo remove também os
> dados hoje ligados ao aluno por FK (contrato, sessões, pagamentos, presenças).
> Quando os setores forem separados, o expurgo passará a **anonimizar** o vínculo
> nos registros de setor em vez de apagá-los, preservando o histórico contábil
> sem dados pessoais.
