# Histórico de Desenvolvimento — SGI-YKR

> Diário de bordo do projeto **Yōkai no Ki SGI**: de onde partiu, como evoluiu e
> para onde vai. Serve como memória do raciocínio de engenharia (útil para o
> portfólio, para o artigo do AWS Builder e para retomar o contexto a qualquer
> momento).

---

## Visão geral

O **SGI-YKR** é um sistema de gestão para um dojo de artes marciais tradicionais
(Kenjutsu/Bujutsu) — o **Yōkai no Ki Ryūha**. É um **monorepo** full-stack:

- **Back-end:** Python · FastAPI · SQLAlchemy · Alembic · SQLite (dev) /
  PostgreSQL (produção).
- **Front-end:** Angular 17 (standalone components) · TailwindCSS (paleta autoral
  *sumi / carmesim / ouro*) · ícones Lucide.
- **Infra:** Docker + Docker Compose · GitHub Actions (CI).

O foco do projeto nunca foi um CRUD genérico, e sim a **modelagem fiel de um
domínio com regras de negócio não-triviais** (cobrança por hora com franquia,
trava de inadimplência, mensalidade gerada pelo calendário, anamnese versionada,
auditoria).

---

## A linha do tempo

### Ponto de partida — o MVP monolítico

O projeto começou como um **monolito**: `main.py` concentrando modelos, schemas e
rotas. Já cobria a operação básica do dojo:

- Matrícula de alunos e secretaria.
- **Modo Tatame** com cronômetro individual e cobrança por sessão.
- Chamada de **Presença** (tela separada).
- Pagamentos com quitação em cascata.
- **Trava automática de inadimplência**.
- Progressão de graduação e *soft delete*.
- ~35 testes.

Em seguida vieram melhorias de **plataforma e portfólio** (antes do roadmap de
produto):

- Migração do front para **Angular 17** standalone + nova paleta visual.
- **Docker / Docker Compose** para subir tudo com um comando.
- Autenticação migrada para **OAuth2 password flow** com JWT.
- **Reorganização** do repositório em `backend/` + `frontend/` na raiz, com
  README de portfólio, LICENSE e documentação de arquitetura.
- **CI** no GitHub Actions (testes do back + build do front).
- Agendador (**APScheduler**) para a trava rodar proativamente de madrugada.
- **Encerramento de matrícula** com dossiê PDF e expurgo agendado (LGPD).

### O roadmap de evolução — 4 pilares

A partir daí, o projeto cresceu em **fases**, cada uma com conceito aprovado,
implementação verificada (testes + build) e commit próprio. A ordem foi definida
por **dependência técnica** (ver `.kiro/specs/evolucao-roadmap-ykr/`).

| Fase | Pilar | Entregou | Commit |
| --- | --- | --- | --- |
| **0** | Técnico | Modularização do monolito em domínios (`models.py`, `schemas.py`, `business/`, `routers/`). | — |
| **1** | Tatame | **Turmas** (molde de aula recorrente), **Calendário** de ocorrências via RRULE, e o **Ambiente Tatame** unificado (fundiu Modo Tatame + Tatame por Turma + Presença). | — |
| **2** | Financeiro | **Conta corrente** (débito × crédito); mensalidade **gerada do calendário**; **abono de falta**. | `402722a` |
| **3** | Anamnese | **Prontuário versionado** (6/12 meses, alerta de vencimento) + **card de alerta crítico** no perfil. | `9d3af4b` |
| **4** | Auditoria | **Log de segurança** (Geral / Sensíveis / por aluno) com retenção de 60 dias. | `1c93f69` |

### Ajustes pós-roadmap (durante os testes)

- **Tela de Gestão de Turmas** (`turmas-panel`): o back-end de Turmas estava
  completo, mas faltava a interface para criá-las — lacuna descoberta ao testar.
  Criada com construtor amigável de recorrência (dias da semana → RRULE),
  vínculo de alunos e geração de ocorrências do mês. Commit `50fc95e`.
- **Restauração do visual dos cards** do Ambiente Tatame ao design original do
  Modo Tatame (formato quadrado, ID, graduação, **alerta médico**, badge de
  imagem), enriquecendo o endpoint de turma com os campos do aluno. Commit
  `e2fb413`.

### Hardening de segurança (pós-roadmap)

Após as 4 fases, iniciou-se o endurecimento de segurança (plano em
`docs/SEGURANCA.md`). Primeira leva — itens **S1, S2 e S3**:

- **S1 — Fail-safe de segredos:** a aplicação **recusa iniciar em produção**
  (banco não-SQLite) se o `JWT_SECRET` ainda for o valor padrão de dev. As
  credenciais iniciais do `create_admin.py` passaram a vir de variáveis de
  ambiente (`YNK_ADMIN*_USER/PASS`), com fallback só em dev.
- **S2 — Política de senha + troca no 1º acesso:** novo campo
  `Usuario.precisa_trocar_senha`; endpoint `POST /auth/trocar-senha` (valida
  senha atual, força da nova e que seja diferente); validador de força (mín. 10
  caracteres, misturando tipos). O **front** mostra um modal bloqueante de troca
  de senha no primeiro login. Commits `d6db2d9` (back) e `0d4728e` (front).
- **S3 — Rate limiting no login:** limitador em memória (5 falhas em 5 min →
  bloqueio de 15 min, por usuário+IP); login bloqueado retorna **429** e o
  bloqueio é registrado na auditoria.

### Estado atual

- Monolito → aplicação **modular por domínio**.
- **121 testes** automatizados no back-end, todos verdes (108 do roadmap + 13 de
  segurança).
- Build do front verde.
- Fases 0–4 implementadas + hardening S1–S3, tudo commitado e no GitHub.
- **Fase 5** (Áreas: Aluno, Professor, Material Didático) com **conceito
  capturado** em `.kiro/specs/evolucao-roadmap-ykr/fase5-areas.md` — é a fronteira
  para o app multiplataforma.
- Segurança: S1–S3 feitos; **S4–S9 pendentes** (ver `docs/SEGURANCA.md`).

---

## Decisões de engenharia que vale registrar

- **Modularização leve, não big-bang.** Os modelos novos vivem agrupados por
  seção no fim de `models.py`, sem reorganizar o legado — reduz risco de quebrar
  o que já passava nos testes.
- **Mensalidade pelo calendário, não pacote fixo.** O valor nasce das aulas
  previstas no mês; só o cancelamento pela escola reduz, falta do aluno não.
  Essa regra determinou a ordem do roadmap (Turmas **antes** de Financeiro).
- **Anamnese coexiste com o legado.** O campo string `restricao_medica` continua
  existindo e é sincronizado ao salvar uma versão nova, para não quebrar telas
  antigas enquanto o modelo versionado assume.
- **Auditoria sem FK para o aluno.** O log precisa **sobreviver ao expurgo**
  (Hard Delete) do aluno — é a prova de que a ação ocorreu (LGPD).
- **Verificação a cada fase.** `pytest` + `ng build` verdes antes de fechar e
  commitar qualquer fase.

---

## Próximos passos (planejados)

1. **Hardening de segurança** — ver [`SEGURANCA.md`](SEGURANCA.md). Prioridade
   antes de abrir o acesso para fora da máquina local.
2. **Fase 5 — Áreas** (Aluno / Professor / Material Didático), começando pela
   fatia de papéis de acesso (`aluno`/`professor`).
3. **Deploy em produção** (nuvem): back-end hospedado com HTTPS, banco gerenciado
   com criptografia em repouso e storage de objetos para o material didático.
4. **App multiplataforma** (Android / iOS / Desktop) consumindo a mesma API
   OAuth2 — o app é o *cliente*; o servidor hospedado é o pré-requisito.
