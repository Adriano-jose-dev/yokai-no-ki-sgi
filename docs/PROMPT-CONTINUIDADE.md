# Prompt de Continuidade — SGI-YKR
> Cole este documento inteiro no início de uma conversa com qualquer assistente
> de IA (Gemini, ChatGPT, etc.) para retomar o desenvolvimento sem perder contexto.
> Última atualização: Setembro/2026. Commit HEAD: `a5e6e86`.

---

## INSTRUÇÕES PARA O ASSISTENTE

Você está assumindo o desenvolvimento de uma aplicação full-stack em andamento.
Leia **todo este documento antes de responder qualquer coisa**. Ele contém o
contexto completo, as decisões tomadas, o que está feito, o que falta e as
regras de negócio. Nunca ignore uma regra de negócio documentada aqui.

Ao receber uma tarefa:
1. Leia o contexto relevante nos arquivos (`docs/`, `.kiro/`) antes de propor código.
2. Siga exatamente as convenções técnicas descritas na seção 4.
3. A cada implementação: rode `pytest -q` (backend) e `ng build` (frontend) para verificar. Não entregue código sem confirmar que está verde.
4. Faça commits específicos com mensagem descritiva. Nunca `git add .`.
5. Nunca use Hard Delete em alunos — apenas Soft Delete (status → Inativo), exceto no fluxo de Encerramento definitivo já implementado.

---

## 1. O QUE É O PROJETO

**SGI-YKR** — Sistema de Gestão Interna do **Yōkai no Ki Ryūha**, um dojo de
artes marciais tradicionais (Kenjutsu/Bujutsu). Sistema de uso interno da
diretoria para:

- Gerenciar alunos, matrículas e contratos.
- Operar o tatame (cronômetro, cobrança por sessão).
- Controlar presença e progressão de graduação.
- Gerir turmas, calendário de aulas e conta corrente financeira.
- Manter prontuário médico (anamnese) versionado com card de alerta crítico.
- Auditar ações sensíveis.

**Repositório GitHub:** `Adriano-jose-dev/yokai-no-ki-sgi` (branch `main`).

**Monorepo em:** `c:\dev\Kiron YnK\` com pastas `backend/` e `frontend/`.

---

## 2. STACK TÉCNICA

```
backend/          Python 3.12 · FastAPI 0.110 · SQLAlchemy 2 · Alembic
                  SQLite (dev) / PostgreSQL (produção)
                  JWT (PyJWT) · bcrypt (passlib) · APScheduler · ReportLab
                  python-dateutil (RRULE) · pytest (121 testes)

frontend/         Angular 17 standalone (sintaxe @if/@for)
                  TailwindCSS · paleta autoral: sumi (índigo), carmesim (vermelho), ouro (dourado)
                  Ícones Lucide (registrados em app.config.ts)
                  HttpClient + authInterceptor (Bearer JWT)

infra             Docker + Docker Compose · GitHub Actions (CI)
```

**CONVENÇÕES OBRIGATÓRIAS:**
- Backend: modelos em `models.py` (agrupados por domínio no fim do arquivo),
  schemas em `schemas.py`, regras de negócio em `business/<dominio>.py` (sem
  FastAPI, sem commit), routers em `routers/<dominio>.py` (orquestram + commitam).
- Frontend: componentes standalone, `ApiService` para todas as chamadas HTTP,
  paleta sumi/carmesim/ouro, nenhum ícone Lucide usado sem registrar em
  `app.config.ts`.
- Nunca usar Hard Delete direto — apenas via fluxo de Encerramento.
- ORM parametrizado (SQLAlchemy) em todas as queries — sem SQL raw.
- Verificar `pytest -q` + `ng build` antes de cada commit.

---

## 3. ESTADO ATUAL — O QUE ESTÁ 100% IMPLEMENTADO

### 3.1 Banco de dados — tabelas existentes (em ordem de migration)

```
alunos               — ficha do aluno (PK: id_matricula = YNK202610001)
contratos            — plano, valor_base, taxa_admissao_saldo, dia_vencimento
sessoes              — cronômetro tatame (hora_entrada/saida, valor_apurado, pago)
pagamentos           — log de recebimentos imutável
presencas            — registro diário de presença por aluno
usuarios             — admin do sistema (role, ativo, precisa_trocar_senha)
encerramentos_matricula — janela 30 dias + dossiê PDF (blob)
turmas               — molde de aula (tipo_pagamento, classe, valor_base, RRULE)
turma_matriculas     — aluno↔turma (papel: matriculado/ocorrente, gratuito)
ocorrencias_aula     — aula numa data (estado: prevista/realizada/cancelada)
lancamentos          — conta corrente (débito/crédito, valor_aberto, mes_referencia)
abonos_falta         — abono justificado (só mensalistas)
anamneses            — prontuário versionado (versao, ativa, respostas_json, validade)
registros_auditoria  — log de segurança SEM FK para aluno (sobrevive ao expurgo)
```

**Cadeia de migrations Alembic (HEAD = c9d0e1f2a3b4):**
```
639d4d737621 → bdf6715ed4b1 → c1a2b3d4e5f6 → d2b3c4e5f6a7 → e3c4d5f6a7b8
→ f4d5e6a7b8c9 → a7b8c9d0e1f2 → b8c9d0e1f2a3 → c9d0e1f2a3b4
```

**ATENÇÃO:** se o banco foi criado antes das migrations (pelo `create_all`
automático do dev), rodar `alembic upgrade head` vai falhar com "table already
exists". Solução: `alembic stamp b8c9d0e1f2a3` → `alembic upgrade head`.

### 3.2 Rotas funcionais

Todas as rotas exigem `Authorization: Bearer <token>` (exceto `/auth/login`).

**Autenticação** (`/auth/login`, `/auth/trocar-senha`)
**Alunos & Secretaria** — 14 rotas em `GET/POST/PUT /alunos/...`
**Tatame** — `GET /tatame/ativos`, `POST /sessao/start`, `POST /sessao/stop`
**Presença** — `GET /presenca/diaria`, `POST /presenca/bulk`
**Pagamentos** — `POST /pagamentos/receber`
**Encerramento** — encerrar, listar, download dossiê, revogar
**Turmas** — CRUD completo + vincular/desvincular aluno
**Calendário/Ocorrências** — gerar da RRULE, listar, avulsa, editar, cancelar, presença, duração
**Financeiro** — conta, previsão mensalidade, gerar débito, pagar, abonar
**Anamnese** — salvar versão, obter ativa+card, histórico
**Auditoria** — listar (geral/sensível), por aluno

**Documentação viva:** `GET /docs` (Swagger) quando o backend está rodando.

### 3.3 Frontend — abas do shell autenticado (home)

| Aba | Componente | O que faz |
|-----|-----------|-----------|
| Ambiente Tatame | `tatame-turma` | Seleciona turma do dia; cards ricos de aluno (quadrado, ID, graduação, alerta médico); cronômetro global (Mensalidade) ou individual (Hora-Aula) |
| Secretaria | `admin-detail` | Perfil do aluno: Resumo / Ficha / Financeiro / Frequência. Card de alerta crítico no topo do Resumo |
| Turmas | `turmas-panel` | Criar turma (seleção de dias → RRULE automática), vincular alunos, gerar ocorrências do mês |
| Calendário | `calendario-panel` | Calendário mensal com bolinhas por aula; clicar no dia mostra participantes |
| Encerradas | `encerradas-panel` | Matrículas em janela de 30 dias; download de dossiê; revogar |
| Auditoria | `auditoria-panel` | Filtros Geral / Sensíveis / por aluno |
| Modal de troca de senha | (no home shell) | Aparece ao logar se `precisa_trocar_senha=true`; bloqueia o sistema até a troca |

### 3.4 Segurança implementada (S1–S3)

- **S1:** `config.validar_seguranca_producao()` no startup — aborta se produção
  + JWT_SECRET padrão.
- **S2:** `Usuario.precisa_trocar_senha`; `POST /auth/trocar-senha`; validador de
  força (min 10 chars, não só dígitos nem só letras); modal bloqueante no front.
- **S3:** `business/ratelimit.py` — 5 falhas em 5 min → bloqueio 15 min
  (usuário+IP); 429 ao bloquear; bloqueio auditado.

---

## 4. REGRAS DE NEGÓCIO — NÃO ALTERAR SEM REVISÃO

### 4.1 Cobrança por sessão de tatame

```
hora_flexivel == True  →  horas × valor_base
Mensalidade            →  max(0, horas - 3) × valor_base  (franquia 3h)
Intensivão             →  horas × (valor_base × 1.5)
Horas Livres           →  horas × valor_base
```
Presença automática é registrada ao encerrar qualquer sessão.

### 4.2 Trava automática de inadimplência

- Só `Mensalidade`. Se `hoje > dia_vencimento + 5 dias` → `Trancado` +
  `[TRAVA AUTOMÁTICA]` na `observacao_financeira`.
- `[ACORDO]` na observação → bypass total.
- Sessão aberta é encerrada ao trancar.
- Aluno `Trancado` não aparece no tatame.
- Avaliação **lazy** nas rotas + APScheduler à meia-noite.

### 4.3 Mensalidade pelo calendário (conta corrente)

- Valor = `Σ (turma.valor_base × horas_da_ocorrência)` do mês.
- Só `prevista`/`realizada` contam; `cancelada` sai da conta.
- **Falta do aluno NÃO altera o valor** — só cancelamento pela escola.
- Geração idempotente por `mes_referencia (YYYY-MM)`.
- Crédito abate débito no momento da geração.

### 4.4 Anamnese versionada

- Validade 6 ou 12 meses. Status: `ok` / `vence_em_breve` (≤30 dias) / `vencida`.
- Card de alerta crítico: condições clinicamente relevantes (asma, cardíaco,
  pressão alta, diabetes, tontura, falta_ar, dores_peito, alergias).
- `cirurgias` NÃO é crítico — fica no prontuário mas não dispara o card.
- Sincroniza `Aluno.restricao_medica` ("Condições: X. Obs: Z") ao salvar.

### 4.5 Auditoria

- **Geral:** fila máx. 50, retida 60 dias. Poda lazy na leitura.
- **Sensível:** isolada, sem poda. Ações: receber pagamento, encerrar/revogar
  matrícula, expurgo, destrancar, suspender, alterar status, login bloqueado,
  trocar senha.
- `RegistroAuditoria` sem FK para aluno (sobrevive ao expurgo LGPD).

### 4.6 Outras regras fixas

- Menor de 18 anos exige `nome_pai` + `nome_mae`.
- `dia_vencimento` só existe para `Mensalidade`.
- Aluno `Encerrado`/`Trancado`/`Inativo` não aparece no tatame.
- Hard Delete só pelo fluxo de Encerramento definitivo.

---

## 5. O QUE FALTA — PRÓXIMOS PASSOS (em prioridade)

### 5.1 Segurança pendente (arquivo: `docs/SEGURANCA.md` local)

| Item | O que é | Prioridade |
|------|---------|-----------|
| **S4** | Token JWT em **cookie httpOnly+SameSite** (hoje está em localStorage = vulnerável a XSS). Access token curto + refresh token. | Alta |
| **S5** | **Security headers** no middleware FastAPI: HSTS, CSP, X-Content-Type-Options, X-Frame-Options. | Média |
| **S6** | **Autorização por propriedade** (anti-IDOR): ao abrir papéis `aluno`/`professor` (Fase 5), garantir que um aluno não lê dados de outro. Testes de 403 cruzado. | Alta (junto da Fase 5) |
| **S7** | **SCA + SAST no CI:** `pip-audit` + `npm audit` + `bandit` no GitHub Actions. Dependabot ligado. | Média |
| **S8** | **Criptografia em repouso:** banco gerenciado com encryption-at-rest (configuração de infra, não código). | Deploy |
| **S9** | **Hardening de infraestrutura:** HTTPS obrigatório, WAF, secrets manager, backups testados. | Deploy |

### 5.2 Fase 5 — Áreas (spec em `.kiro/specs/evolucao-roadmap-ykr/fase5-areas.md`)

Três áreas novas + autenticação multi-papel. **Faseamento sugerido:**

**5a — Papéis de acesso** (menor esforço, maior impacto, nenhuma decisão em aberto):
- Adicionar papéis `aluno` e `professor` ao modelo `Usuario`.
- Vínculo `Usuario.id_aluno` → `Aluno.id_matricula`.
- `Turma.id_professor` → `Usuario.id`.
- Testes de autorização cruzada (S6): aluno A não acessa dados de aluno B (403).
- Rotas "meus dados" filtradas pelo token.

**5b — Área do Aluno:**
- `GET /meu/progresso`, `GET /meu/calendario`, `GET /meu/conta`, `GET /meu/presencas`.
- Aluno vê apenas os próprios dados.

**5c — Área do Professor:**
- Ambiente Tatame restrito às turmas do professor.
- Card de alerta crítico visível para o professor.

**5d — Material Didático:**
- Modelo `MaterialDidatico` (título, tipo, url_ou_corpo, id_turma, graduacao_alvo, publicado).
- Visibilidade por turma/graduação.
- Decisão pendente: **link externo** (simples) vs **upload** (precisa de storage S3).

**5e — Consumo + Auditoria:**
- Modelo `ConsumoMaterial` (id_material, id_aluno, evento: abriu/marcou_lido, segundos).
- Eventos alimentam a auditoria (categoria `material`).

### 5.3 Deploy em produção

- Back-end: servidor com HTTPS, PostgreSQL gerenciado (RDS), encryption-at-rest.
- Front-end: Nginx servindo o build Angular, proxy `/api` → backend.
- Storage: S3 (ou equivalente) para material didático.
- Secrets manager para `JWT_SECRET`, `DATABASE_URL`, credenciais.
- AWS (AWS Builder ID do dono) é o provedor preferido.

### 5.4 App multiplataforma (futuro)

- Android / iOS / Desktop consumindo a **mesma API OAuth2** existente.
- O app é o *cliente* — o servidor hospedado é o pré-requisito.
- Tecnologia não decidida (possíveis: Capacitor sobre o Angular, Flutter, React Native).

---

## 6. COMO RODAR LOCALMENTE

```powershell
# Terminal 1 — Backend (PowerShell, pasta backend/)
cd "C:\dev\Kiron YnK\backend"
pip install -r requirements.txt

# ATENÇÃO: se o banco foi criado antes de rodar o Alembic:
alembic stamp b8c9d0e1f2a3    # sincroniza banco antigo
alembic upgrade head           # aplica migrations pendentes

python create_admin.py         # cria usuários (idempotente)
uvicorn main:app --reload      # API em http://localhost:8000
                               # Swagger em http://localhost:8000/docs

# Terminal 2 — Frontend (PowerShell, pasta frontend/)
cd "C:\dev\Kiron YnK\frontend"
# Se der erro de "execução de scripts desabilitada":
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
npm install
npm start                      # App em http://localhost:4200
```

**Login:** credenciais em `backend/create_admin.py` (variável `USUARIOS_INICIAIS`).
No primeiro login: modal de troca de senha obrigatória. Use senha forte (10+
chars, misturado — ex.: `Yokai@Dojo2026`).

**Python global** (se não tiver venv): use o caminho completo:
`C:\Users\home\AppData\Local\Programs\Python\Python312\python.exe`

---

## 7. ARQUIVOS DE REFERÊNCIA NO PROJETO

| Arquivo | Conteúdo |
|---------|----------|
| `docs/ESTADO-TECNICO.md` | Snapshot técnico: models, schemas, routers, migrações, testes |
| `docs/HISTORICO-DESENVOLVIMENTO.md` | Jornada do projeto (decisões de engenharia) |
| `docs/SEGURANCA.md` | Plano de segurança com checklist S1–S9 (**local, não versionado**) |
| `.kiro/steering/regras-negocio-ykr.md` | Regras de negócio completas (fonte da verdade) |
| `.kiro/specs/evolucao-roadmap-ykr/fase5-areas.md` | Spec da Fase 5 (Áreas) |
| `backend/models.py` | Todos os modelos SQLAlchemy |
| `backend/schemas.py` | Todos os schemas Pydantic |
| `backend/requirements.txt` | Dependências com versões fixadas |
| `README.md` | README do portfólio (público, no GitHub) |

---

## 8. CONTEXTO DO DONO DO PROJETO

- **Objetivo de uso:** sistema para uso diário real do dojo.
- **Objetivo de portfólio:** projeto técnico para o AWS Builder ID (artigo
  planejado depois que o app estiver "redondo").
- **Disciplina paralela:** projeto de "Tópicos em Big Data Python" com Power BI
  — é **outro repositório separado**, pode usar dados do SGI como dataset.
- **Prioridade atual:** deixar o app seguro e funcional para uso diário
  **antes** de publicar artigo ou começar o app mobile.
- **Sobre segurança:** apenas hardening **defensivo** — proteger a aplicação e
  os dados dos alunos (incluindo dados de saúde e de menores de 18 anos, LGPD).
  Nada ofensivo.

---

## 9. ESTADO DO MVP PARA USO DIÁRIO

O sistema já é **operacionalmente viável** para uso interno da diretoria. Um
administrador consegue hoje:

✅ Matricular alunos (experimental ou completo), com validação de menoridade.
✅ Criar turmas com recorrência e gerar o calendário de aulas do mês.
✅ Operar o Ambiente Tatame: abrir a turma do dia, marcar presença/ausência
   (mensalidade) ou iniciar/parar cronômetro individual (hora-aula).
✅ Ver e gerenciar a conta corrente de cada aluno: gerar mensalidade pelo
   calendário, registrar pagamento, ver saldo.
✅ Preencher e versionar a anamnese do aluno; ver o card de alerta crítico
   (condições de saúde que interferem na aula) no perfil.
✅ Consultar o log de auditoria de ações sensíveis.
✅ Encerrar matrícula com geração de dossiê PDF e janela de revogação de 30 dias.
✅ Trocar senha com política de força no primeiro acesso (S2).

⚠️ **O que ainda impede uso em produção (fora da máquina local):**
- Sem servidor hospedado com HTTPS (S9) — hoje só funciona em `localhost`.
- Token JWT no localStorage (S4) — vulnerável a XSS se exposto na internet.
- Credenciais e secrets ainda precisam migrar para um secrets manager (S1/S9
  completo).

**Conclusão:** para uso diário **interno** (dentro da rede local / mesma máquina),
o sistema está pronto. Para abertura externa (alunos acessando, professor
acessando de casa, app mobile), precisa do deploy seguro (S4, S8, S9) e da
Fase 5 (papéis aluno/professor).
