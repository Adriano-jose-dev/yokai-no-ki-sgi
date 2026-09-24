<div align="center">

# 🥷 Yōkai no Ki SGI

**Sistema de Gestão Interna para um Dojo de artes marciais tradicionais** (Kenjutsu / Bujutsu).

Uma aplicação full-stack que informatiza a operação diária de uma escola marcial — matrícula, controle de tatame com cobrança por sessão, chamada de presença, progressão de graduação e gestão financeira com trava automática de inadimplência.

[![CI](https://github.com/adriano-jose-peixoto/yokai-no-ki-sgi/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/adriano-jose-peixoto/yokai-no-ki-sgi/actions/workflows/ci.yml)
![Angular](https://img.shields.io/badge/Angular-17-DD0031?logo=angular&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)

</div>

---

## 📖 Sobre o projeto

O **Yōkai no Ki SGI** nasceu de um problema real: gerir um dojo envolve regras de negócio específicas que planilhas não dão conta — tempo de treino cobrado por hora com franquias, bloqueio automático de alunos inadimplentes, réguas de progressão por faixa, e controle de presença integrado ao cronômetro do tatame.

Este repositório é um **monorepo** com uma API REST em FastAPI e uma SPA em Angular, containerizados e prontos para produção. O foco não é um CRUD genérico: é a **modelagem fiel de um domínio com regras não-triviais**.

---

## 🧩 Regras de negócio (o coração do sistema)

O que torna este projeto interessante são as regras que ele automatiza:

### Cobrança por sessão de tatame
Ao encerrar uma sessão, o tempo é convertido em horas decimais e o custo é calculado conforme o plano:

| Plano | Fórmula |
| --- | --- |
| **Hora Flexível** | `horas × valor_base` |
| **Mensalidade** | `(horas − 3) × valor_base` — franquia de 3h; nunca negativo |
| **Intensivão** | `horas × (valor_base × 1.5)` |
| **Horas Livres** | `horas × valor_base` |

### Trava automática de inadimplência
- Aplica-se **apenas** ao plano Mensalidade.
- Passados **5 dias** do vencimento, o aluno é automaticamente `Trancado` e uma sessão aberta é encerrada na hora.
- O marcador `[ACORDO]` na observação financeira faz **bypass** total da trava.
- Avaliação **lazy** (nas rotas) + um **job diário via APScheduler** que varre o banco de madrugada.

### Progressão marcial
- **Gakusei** (Ashigaru / Kyu): meta de **5 meses** por faixa.
- **Bushi / Dan**: meta de **12 meses**. A API sempre retorna quantos meses faltam para o próximo exame.

### Soft delete
Alunos nunca são apagados do banco — o status muda para `Inativo`, preservando todo o histórico.

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
- **Documentação viva**: Swagger em `/docs`, com as regras de negócio descritas em cada endpoint.

> 📐 Diagramas detalhados (containers, fluxo de autenticação e da trava de inadimplência) em **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## 🛠️ Stack

**Front-end**
- Angular 17 (standalone components, nova sintaxe de fluxo `@if`/`@for`)
- TailwindCSS (paleta autoral "sumi / carmesim / ouro", tema marcial)
- Ícones Lucide (SVG)

**Back-end**
- FastAPI + Uvicorn (ASGI)
- SQLAlchemy 2 + Alembic
- Autenticação JWT (PyJWT) + OAuth2 + passlib/bcrypt
- APScheduler (job agendado)
- Pytest (35 testes)

**Infra**
- PostgreSQL 16
- Docker + Docker Compose (sobe tudo com um comando)
- GitHub Actions (CI: testes do back + build do front)

---

## 📂 Estrutura

```
yokai-no-ki-sgi/
├── backend/              # API FastAPI
│   ├── business/         # regras de negócio (trava, cobrança, agendador)
│   ├── routers/          # endpoints por domínio
│   ├── alembic/          # migrations
│   ├── main.py           # entrypoint ASGI
│   └── requirements.txt
├── frontend/             # SPA Angular 17
│   └── src/app/          # componentes standalone + services
├── docker-compose.yml    # orquestração completa
├── README_DEPLOY.md      # guia de deploy em produção
└── .github/workflows/    # CI
```

---

## 🚀 Como rodar

### Opção 1 — Docker (recomendado, um comando)

```bash
docker compose up --build
```
- Front: <http://localhost:8080>
- API / Swagger: <http://localhost:8000/docs>

### Opção 2 — Local (desenvolvimento)

**Back-end** (em `backend/`):
```bash
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1   |   Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python create_admin.py        # cria os usuários iniciais
uvicorn main:app --reload
```

**Front-end** (em `frontend/`):
```bash
npm install
npm start                     # http://localhost:4200
```

> Guia completo de produção (PostgreSQL, variáveis de ambiente, build): veja **[README_DEPLOY.md](README_DEPLOY.md)**.

---

## ✅ Testes

```bash
cd backend
pytest -q          # 35 testes: cobrança, trava, soft delete, auth, agendador
```

---

## 📌 Roadmap

- [ ] Papel `sensei` (autorização restrita ao Tatame) — arquitetura já preparada no JWT
- [ ] Dashboard de indicadores (alunos ativos, inadimplentes, próximos exames)
- [ ] App mobile (APK) consumindo a API OAuth2
- [ ] Rate limiting no login e refresh tokens

---

<div align="center">
<sub>Projeto de portfólio · desenvolvido por <a href="https://github.com/adriano-jose-peixoto">Adriano José Peixoto</a></sub>
</div>
