<div align="center">

# 🥷 Yōkai no Ki SGI

**Sistema de Gestão Interna para um Dojo de artes marciais tradicionais** (Kenjutsu / Bujutsu).

Uma aplicação full-stack que informatiza a operação diária de uma escola marcial — matrícula, turmas e calendário de aulas, controle de tatame com cobrança por sessão, conta corrente financeira, prontuário médico (anamnese) versionado, progressão de graduação e log de auditoria.

[![CI](https://github.com/Adriano-jose-dev/yokai-no-ki-sgi/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Adriano-jose-dev/yokai-no-ki-sgi/actions/workflows/ci.yml)
![Angular](https://img.shields.io/badge/Angular-17-DD0031?logo=angular&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)
![Testes](https://img.shields.io/badge/testes-108%20passing-brightgreen)

</div>

---

## 📖 Sobre o projeto

O **Yōkai no Ki SGI** nasceu de um problema real: gerir um dojo envolve regras de negócio específicas que planilhas não dão conta — tempo de treino cobrado por hora com franquias, bloqueio automático de alunos inadimplentes, réguas de progressão por faixa e controle de presença integrado ao cronômetro do tatame.

Este repositório é um **monorepo** com uma API REST em FastAPI e uma SPA em Angular, containerizados e prontos para produção. O foco não é um CRUD genérico: é a **modelagem fiel de um domínio com regras não-triviais**.

---

## 🧭 Evolução: o "antes" e o "agora"

Este projeto cresceu em fases, cada uma commitada e verificada (testes + build). Vale registrar de onde ele partiu e onde chegou — a parte mais interessante da história é a **evolução arquitetural**.

### O "antes" (MVP inicial)

- Um backend **monolítico** (`main.py` concentrando models, schemas e rotas).
- Operação do dia a dia: matrícula, **Modo Tatame** com cronômetro individual e cobrança por sessão, chamada de **Presença** separada, pagamentos com quitação em cascata e a **trava de inadimplência**.
- Progressão de graduação e soft delete.
- ~35 testes.

### O "agora" (após o roadmap de 4 pilares)

| Fase | Pilar | O que entrou |
| --- | --- | --- |
| **0** | Técnico | **Modularização** do monolito em domínios: `models.py`, `schemas.py`, `business/` e `routers/` separados por responsabilidade. |
| **1** | Tatame | **Turmas** (molde de aula recorrente, com valor base e classe Dojo/Legado), **Calendário** de ocorrências geradas por recorrência (RRULE), e o **Ambiente Tatame** unificado — que fundiu Modo Tatame + Tatame por Turma + Presença numa só tela, com cronômetro individual (Hora-Aula) e global + presença por aluno (Mensalidade). |
| **2** | Financeiro | **Conta corrente** (débito × crédito): a mensalidade é **gerada do calendário** (`valor_base × horas previstas das aulas do mês`), aula cancelada pela escola reduz o valor, falta do aluno não; crédito abate débito; **abono de falta** para mensalistas. |
| **3** | Anamnese | **Prontuário médico versionado**: cada preenchimento gera uma versão (as antigas viram histórico), com validade de 6/12 meses e alerta de vencimento, e um **card de alerta crítico** no perfil (condições que interferem na aula + contatos de emergência). |
| **4** | Auditoria | **Log de segurança** exclusivo de admins: registra ações sensíveis (editar contrato, receber pagamento, encerrar matrícula, etc.) com recortes **Geral / Sensíveis / por aluno** e retenção de 60 dias. |

Resultado: de um MVP monolítico para uma aplicação **modular por domínios**, com **108 testes** e cobertura das regras de cada pilar.

> 🔭 **Próximo (Fase 5, planejada):** áreas do **Aluno**, do **Professor** e de **Material Didático** (com eventos de consumo alimentando a auditoria), abrindo caminho para o app multiplataforma. Conceito capturado em [`.kiro/specs/`](.kiro/specs/).

---

## 🧩 Regras de negócio (o coração do sistema)

### Cobrança por sessão de tatame
Ao encerrar uma sessão, o tempo é convertido em horas decimais e o custo é calculado conforme o plano:

| Plano | Fórmula |
| --- | --- |
| **Hora Flexível** | `horas × valor_base` |
| **Mensalidade** | `(horas − 3) × valor_base` — franquia de 3h; nunca negativo |
| **Intensivão** | `horas × (valor_base × 1.5)` |
| **Horas Livres** | `horas × valor_base` |

### Mensalidade pelo calendário (conta corrente)
A mensalidade do mês é **somada a partir das aulas previstas no calendário** da(s) turma(s) do aluno (`valor_base × horas`), não um pacote fixo. Só o **cancelamento de aula pela escola** reduz o valor; falta do aluno não altera. No vencimento, o valor vira **débito** na conta corrente, abatido por crédito disponível.

### Trava automática de inadimplência
- Aplica-se **apenas** ao plano Mensalidade.
- Passados **5 dias** do vencimento, o aluno é automaticamente `Trancado` e uma sessão aberta é encerrada na hora.
- O marcador `[ACORDO]` na observação financeira faz **bypass** total da trava.
- Avaliação **lazy** (nas rotas) + um **job diário via APScheduler** que varre o banco de madrugada.

### Anamnese versionada + alerta crítico
Prontuário refeito a cada 6/12 meses; as versões antigas viram histórico. O sistema extrai da versão ativa um **card de alerta crítico** (asma, cardíaco, pressão alta, etc. + contatos de emergência) e avisa quando a ficha vence.

### Auditoria
Toda ação sensível é registrada (quem fez, o quê, quando, sobre qual aluno). O log **sobrevive ao expurgo** do aluno (LGPD) — é a prova de que a ação ocorreu.

### Progressão marcial
- **Gakusei** (Ashigaru / Kyu): meta de **5 meses** por faixa.
- **Bushi / Dan**: meta de **12 meses**. A API sempre retorna quantos meses faltam para o próximo exame.

### Ciclo de vida da matrícula
- **Suspensão** (soft delete, reversível): o aluno some das telas, mas o vínculo e o histórico ficam.
- **Encerramento** (definitivo): gera um **dossiê PDF**, retém por 30 dias (com revogação possível) e então faz o **Hard Delete** (LGPD).

---

## 🏛️ Arquitetura

```
┌─────────────┐      HTTP/JSON      ┌──────────────┐     SQL      ┌──────────────┐
│   Angular    │  ───────────────>  │   FastAPI     │  ────────>  │  PostgreSQL   │
│   (SPA)      │   Bearer (JWT)     │   (ASGI)      │  SQLAlchemy │              │
│  Nginx :80   │  <───────────────  │   :8000       │  + Alembic  │              │
└─────────────┘                    └──────────────┘             └──────────────┘
      │                                    │
   proxy /api                        APScheduler (job diário da trava)
```

- **Autenticação**: OAuth2 *password flow* com JWT (bcrypt para senhas, `role` no token para autorização por papéis).
- **Migrations**: Alembic gere o esquema em produção.
- **Modularização por domínio**: cada pilar vive em seu próprio `business/<dominio>.py` + `routers/<dominio>.py` + testes, sobre modelos agrupados por seção em `models.py`.
- **Documentação viva**: Swagger em `/docs`, com as regras de negócio descritas em cada endpoint.

> 📐 Diagramas detalhados em **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## 🛠️ Stack

**Front-end**
- Angular 17 (standalone components, sintaxe `@if`/`@for`)
- TailwindCSS (paleta autoral "sumi / carmesim / ouro", tema marcial)
- Ícones Lucide (SVG)

**Back-end**
- FastAPI + Uvicorn (ASGI)
- SQLAlchemy 2 + Alembic
- Autenticação JWT (PyJWT) + OAuth2 + passlib/bcrypt
- APScheduler (job agendado) · python-dateutil (recorrência RRULE do calendário) · ReportLab (dossiê PDF)
- Pytest (**108 testes**)

**Infra**
- PostgreSQL 16 (SQLite no desenvolvimento)
- Docker + Docker Compose
- GitHub Actions (CI: testes do back + build do front)

---

## 📂 Estrutura

```
yokai-no-ki-sgi/
├── backend/              # API FastAPI
│   ├── business/         # regras de negócio por domínio
│   │   ├── trava.py          #   inadimplência
│   │   ├── ocorrencias.py    #   calendário / RRULE
│   │   ├── financeiro.py     #   conta corrente
│   │   ├── anamnese.py       #   prontuário versionado
│   │   ├── auditoria.py      #   log de segurança
│   │   └── scheduler.py      #   job diário
│   ├── routers/          # endpoints por domínio
│   ├── alembic/          # migrations
│   ├── main.py           # entrypoint ASGI
│   └── requirements.txt
├── frontend/             # SPA Angular 17
│   └── src/app/          # componentes standalone + services
├── .kiro/specs/          # specs do roadmap de evolução
├── docker-compose.yml
├── README_DEPLOY.md      # guia de deploy em produção
└── .github/workflows/    # CI
```

---

## 🚀 Como rodar e testar agora

### Opção 1 — Docker (um comando)

```bash
docker compose up --build
```
- Front: <http://localhost:8080>
- API / Swagger: <http://localhost:8000/docs>

### Opção 2 — Local (desenvolvimento)

Você vai precisar de **dois terminais**: um para o back-end e outro para o front-end.

#### Terminal 1 — Back-end (pasta `backend/`)

```powershell
# (opcional, recomendado) criar e ativar um ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate         # Linux / macOS

pip install -r requirements.txt

# cria/atualiza o esquema do banco (inclui as tabelas novas:
# turmas, ocorrencias, lancamentos, anamneses, registros_auditoria...)
alembic upgrade head

python create_admin.py             # cria os usuários iniciais da diretoria
uvicorn main:app --reload          # sobe a API em http://localhost:8000
```

> **Importante:** sempre rode `alembic upgrade head` depois de atualizar o
> projeto — as fases do roadmap adicionaram tabelas novas. Sem isso, as telas de
> Turmas, Financeiro, Anamnese e Auditoria falham por tabela inexistente.

#### Terminal 2 — Front-end (pasta `frontend/`)

```bash
npm install
npm start                          # http://localhost:4200
```

#### Login para testar

Abra <http://localhost:4200> e entre com um dos usuários criados pelo `create_admin.py`:

| Usuário | Senha |
| --- | --- |
| `sawayama.naryu` | `Yokai2026*` |
| `sumiyoshi.kaito` | `Yokai2026*` |

> São credenciais de MVP, chumbadas só para o primeiro acesso — troque em uso real.

#### Roteiro rápido de teste

1. **Secretaria** → matricular um aluno (mensalista, com dia de vencimento).
2. **Secretaria → aba Ficha** → preencher a **Anamnese** (marque uma condição crítica e veja o card de alerta aparecer no Resumo).
3. Criar uma **Turma** de Mensalidade com recorrência e gerar as ocorrências no **Calendário**.
4. **Secretaria → aba Financeiro** → *Gerar Mensalidade* (o valor vem do calendário) e *Registrar Pagamento*.
5. **Ambiente Tatame** → iniciar/encerrar uma aula.
6. **Auditoria** → ver as ações que você acabou de fazer registradas.

> Guia completo de produção (PostgreSQL, variáveis de ambiente, build): veja **[README_DEPLOY.md](README_DEPLOY.md)**.

---

## ✅ Testes automatizados

Suíte com **108 testes** cobrindo cobrança por sessão, trava de inadimplência, turmas e ocorrências, conta corrente, anamnese versionada, auditoria, soft delete, autenticação e o agendador:

```bash
cd backend
pytest -q
```

---

## 📌 Roadmap

- [x] **Fase 1** — Turmas, Calendário e Ambiente Tatame unificado
- [x] **Fase 2** — Financeiro (conta corrente, mensalidade por calendário, abono)
- [x] **Fase 3** — Anamnese versionada + card de alerta crítico
- [x] **Fase 4** — Auditoria (log de segurança)
- [ ] **Fase 5** — Áreas do Aluno, do Professor e de Material Didático
- [ ] App multiplataforma (Android / iOS / Desktop) consumindo a API OAuth2
- [ ] Papel `sensei` (autorização restrita ao Tatame) — arquitetura já preparada no JWT
- [ ] Dashboard de indicadores (alunos ativos, inadimplentes, próximos exames)

---

<div align="center">
<sub>Projeto de portfólio · desenvolvido por <a href="https://github.com/Adriano-jose-dev">Adriano José Peixoto</a></sub>
</div>
