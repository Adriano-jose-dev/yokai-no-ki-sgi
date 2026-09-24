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
- **Bloqueio de Deletes:** Nunca utilizar Hard Delete (excluir do banco) para
  alunos. Utilizar sempre **Soft Delete** (mudar status para `Inativo`).
