# Estado Técnico — SGI-YKR
> Snapshot do estado atual da aplicação para fins de documentação técnica.
> Gerado em: Setembro/2026. Último commit: `c506d1a`.
> Testes: **121 passing**. Build frontend: **verde**.

---

## 1. Estrutura de Pastas

```
yokai-no-ki-sgi/                        # raiz do monorepo
│
├── backend/                            # API FastAPI
│   ├── alembic/
│   │   └── versions/
│   │       ├── 639d4d737621_esquema_inicial.py
│   │       ├── bdf6715ed4b1_corrige_horas_franquia_4_para_3.py
│   │       ├── c1a2b3d4e5f6_encerramento_matricula.py
│   │       ├── d2b3c4e5f6a7_turmas.py
│   │       ├── e3c4d5f6a7b8_ocorrencias_aula.py
│   │       ├── f4d5e6a7b8c9_financeiro_conta_corrente.py
│   │       ├── a7b8c9d0e1f2_anamnese_versionada.py
│   │       ├── b8c9d0e1f2a3_auditoria_log.py
│   │       └── c9d0e1f2a3b4_usuario_precisa_trocar_senha.py
│   │
│   ├── business/                       # regras de negócio (sem FastAPI)
│   │   ├── anamnese.py                 # prontuário versionado + card de alerta
│   │   ├── auditoria.py                # log de segurança + retenção
│   │   ├── auth.py                     # JWT, bcrypt, validação de senha, roles
│   │   ├── dossie.py                   # geração do PDF de encerramento
│   │   ├── financeiro.py               # conta corrente, mensalidade pelo calendário
│   │   ├── helpers.py                  # formata_hora, encerrar_sessao_aberta
│   │   ├── ocorrencias.py              # expansão RRULE, geração de ocorrências
│   │   ├── ratelimit.py                # rate limiting em memória (login)
│   │   ├── scheduler.py                # APScheduler — job diário da trava
│   │   └── trava.py                    # trava automática de inadimplência
│   │
│   ├── routers/                        # endpoints por domínio
│   │   ├── alunos.py                   # secretaria (matrícula, ficha, contrato...)
│   │   ├── anamnese.py                 # prontuário versionado
│   │   ├── auditoria.py                # log de segurança
│   │   ├── auth.py                     # login + troca de senha
│   │   ├── encerramento.py             # encerramento definitivo + dossiê PDF
│   │   ├── financeiro.py               # conta corrente, mensalidade, abono
│   │   ├── ocorrencias.py              # calendário de aulas
│   │   ├── pagamentos.py               # recebimento (secretaria)
│   │   ├── presenca.py                 # chamada diária
│   │   ├── tatame.py                   # sessões do tatame legado
│   │   └── turmas.py                   # gestão de turmas
│   │
│   ├── config.py                       # variáveis de ambiente + fail-safe S1
│   ├── conftest.py                     # fixtures pytest (banco em memória)
│   ├── create_admin.py                 # provisionamento de usuários iniciais
│   ├── database.py                     # engine SQLAlchemy + get_db
│   ├── main.py                         # entrypoint ASGI + lifespan + CORS
│   ├── models.py                       # todos os modelos SQLAlchemy
│   ├── schemas.py                      # todos os schemas Pydantic
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── test_*.py                       # 12 arquivos de testes (121 casos)
│
├── frontend/                           # SPA Angular 17
│   └── src/app/
│       ├── admin-detail/               # perfil do aluno (secretaria)
│       ├── anamnese-panel/             # prontuário versionado + card de alerta
│       ├── auditoria-panel/            # log de segurança (Geral/Sensíveis/Aluno)
│       ├── calendario-panel/           # calendário de ocorrências
│       ├── conta-corrente-panel/       # conta corrente (saldo + extrato + ações)
│       ├── daily-panel/                # modo tatame legado (mantido, não exposto)
│       ├── encerradas-panel/           # matrículas encerradas (janela 30 dias)
│       ├── home/                       # shell autenticado (abas + modal troca senha)
│       ├── login/                      # tela de login OAuth2
│       ├── matricula-form/             # formulário de nova matrícula
│       ├── presenca-panel/             # presença legada (mantida, não exposta)
│       ├── services/                   # ApiService, AuthService, authInterceptor
│       ├── tatame-turma/               # Ambiente Tatame (cards ricos + cronômetros)
│       └── turmas-panel/               # gestão de turmas
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── HISTORICO-DESENVOLVIMENTO.md    # jornada do projeto (versionado)
│   ├── ESTADO-TECNICO.md               # este arquivo (versionado)
│   └── SEGURANCA.md                    # plano de segurança (local, não versionado)
│
├── .kiro/specs/evolucao-roadmap-ykr/   # specs do roadmap
│   ├── requirements.md
│   ├── roadmap.md
│   └── fase5-areas.md                  # conceito da Fase 5
│
├── docker-compose.yml
├── README.md
└── README_DEPLOY.md
```

---

## 2. Modelos (models.py) — tabelas do banco

### Domínio Core (legado estabilizado)

| Modelo | Tabela | Descrição |
|---|---|---|
| `Aluno` | `alunos` | Ficha completa do aluno. PK: `id_matricula` (formato `YNK202610001`). Inclui `restricao_medica` (string legada, sincronizada pela anamnese). |
| `Contrato` | `contratos` | Plano, valor base, taxa de admissão, franquia de horas, vencimento. |
| `Sessao` | `sessoes` | Cronômetro de tatame (entrada/saída/valor apurado/diário). |
| `Pagamento` | `pagamentos` | Recebimento registrado (log imutável). |
| `Presenca` | `presencas` | Registro de presença por aluno/data. |
| `Usuario` | `usuarios` | Admin do sistema. Campos: `role`, `ativo`, `precisa_trocar_senha` (S2). |
| `EncerramentoMatricula` | `encerramentos_matricula` | Janela de 30 dias + dossiê PDF binário. |

### Domínio Turmas (Fase 1)

| Modelo | Tabela | Descrição |
|---|---|---|
| `Turma` | `turmas` | Molde de aula: tipo pagamento, classe, valor_base, RRULE, horários. |
| `TurmaMatricula` | `turma_matriculas` | Associação aluno↔turma com papel (`matriculado`/`ocorrente`) e flag `gratuito`. |
| `OcorrenciaAula` | `ocorrencias_aula` | Aula numa data específica. Estados: `prevista`/`realizada`/`cancelada`. |

### Domínio Financeiro (Fase 2)

| Modelo | Tabela | Descrição |
|---|---|---|
| `Lancamento` | `lancamentos` | Razão de débito/crédito. Campos: `tipo`, `categoria`, `valor`, `valor_aberto`, `status`, `mes_referencia`. |
| `AbonoFalta` | `abonos_falta` | Abono justificado (só mensalistas, não altera valor). |

### Domínio Anamnese (Fase 3)

| Modelo | Tabela | Descrição |
|---|---|---|
| `Anamnese` | `anamneses` | Versão da ficha médica. Campos: `versao`, `ativa`, `validade_meses`, `data_validade`, `respostas_json`, `condicoes_criticas_json`, `observacao`, contatos snapshot, `autor`. |

### Domínio Auditoria (Fase 4)

| Modelo | Tabela | Descrição |
|---|---|---|
| `RegistroAuditoria` | `registros_auditoria` | Entrada do log. Sem FK para aluno (sobrevive ao expurgo). Campos: `categoria`, `acao`, `id_aluno`, `autor`, `descricao`, `detalhes_json`. |

---

## 3. Schemas Pydantic (schemas.py) — contratos de entrada da API

### Core / Secretaria
| Schema | Uso |
|---|---|
| `NovoAlunoRequest` | `POST /alunos/matricula` e `PUT /alunos/{id}/upgrade` |
| `EditarFichaRequest` | `PUT /alunos/{id}/editar` |
| `EditarContratoRequest` | `PUT /alunos/{id}/contrato` |
| `AtualizarValorBaseRequest` | `PUT /alunos/{id}/valor-base` |
| `PromoverRequest` | `PUT /alunos/{id}/promover` |
| `StatusRequest` | `PUT /alunos/{id}/status` |
| `UpdateNotaRequest` | `PUT /alunos/{id}/nota-financeira` e `/diario-pedagogico` |

### Tatame
| Schema | Uso |
|---|---|
| `SessaoRequest` | `POST /sessao/start` |
| `StopSessaoRequest` | `POST /sessao/stop` |

### Presença
| Schema | Uso |
|---|---|
| `PresencaItem` + `PresencaBulkRequest` | `POST /presenca/bulk` |
| `ChamadaRequest` / `ListarChamadaRequest` | rotas de chamada |

### Pagamentos
| Schema | Uso |
|---|---|
| `ReceberPagamentoRequest` | `POST /pagamentos/receber` |

### Autenticação (+ Segurança)
| Schema | Uso |
|---|---|
| `TokenResponse` | resposta de `POST /auth/login` (inclui `precisa_trocar_senha`) |
| `TrocarSenhaRequest` | `POST /auth/trocar-senha` |
| `LoginRequest` | schema legado (não usado na rota OAuth2, mantido por compatibilidade) |

### Turmas (Fase 1)
| Schema | Uso |
|---|---|
| `NovaTurmaRequest` | `POST /turmas` |
| `EditarTurmaRequest` | `PUT /turmas/{id}` |
| `VincularAlunoTurmaRequest` | `POST /turmas/{id}/alunos` |
| `MatriculaTurmaItem` | item interno de `NovaTurmaRequest` |

### Calendário / Ocorrências (Fase 1b/1d)
| Schema | Uso |
|---|---|
| `GerarOcorrenciasRequest` | `POST /turmas/{id}/ocorrencias/gerar` |
| `NovaOcorrenciaAvulsaRequest` | `POST /ocorrencias/avulsa` |
| `EditarOcorrenciaRequest` | `PUT /ocorrencias/{id}` |
| `PresencaOcorrenciaRequest` | `POST /ocorrencias/{id}/presenca` |
| `DuracaoRealRequest` | `PUT /ocorrencias/{id}/duracao` |

### Financeiro (Fase 2)
| Schema | Uso |
|---|---|
| `GerarMensalidadeRequest` | `POST /financeiro/{id}/mensalidade/gerar` |
| `PagamentoContaRequest` | `POST /financeiro/{id}/pagar` |
| `AbonoFaltaRequest` | `POST /financeiro/abono` |

### Anamnese (Fase 3)
| Schema | Uso |
|---|---|
| `SalvarAnamneseRequest` | `POST /anamnese/{id_aluno}` |

---

## 4. Rotas funcionais por domínio

### Autenticação (`routers/auth.py`) — tag: Autenticação
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/login` | OAuth2 password flow. Retorna JWT + `precisa_trocar_senha`. Rate limiting: 5 falhas → bloqueio 15 min. |
| `POST` | `/auth/trocar-senha` | Troca a senha do usuário autenticado. Valida força + diferença da atual. |

### Alunos & Secretaria (`routers/alunos.py`) — tag: Alunos & Secretaria
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/alunos` | Lista resumida (id, nome, status). Exclui `Encerrado`. |
| `POST` | `/alunos/matricula` | Cria aluno + contrato. Gera `id_matricula`. |
| `PUT` | `/alunos/{id}/upgrade` | Atualiza ficha + contrato (ex.: experimental → oficial). |
| `PUT` | `/alunos/{id}/editar` | Edita dados cadastrais. |
| `PUT` | `/alunos/{id}/contrato` | Edita contrato + reavalia trava de inadimplência. |
| `PUT` | `/alunos/{id}/valor-base` | Atualiza só o valor base. |
| `PUT` | `/alunos/{id}/destrancar` | Libera aluno trancado; insere `[ACORDO]`. |
| `GET` | `/alunos/{id}/progresso` | Painel completo (ficha, progressão, pendências, histórico). Avalia trava lazy. |
| `PUT` | `/alunos/{id}/promover` | Registra nova graduação. |
| `PUT` | `/alunos/{id}/status` | Altera status. Encerra sessão aberta se trancado/inativo. |
| `PUT` | `/alunos/{id}/desativar` | Soft delete → `Inativo`. |
| `PUT` | `/alunos/{id}/nota-financeira` | Salva observação financeira. |
| `PUT` | `/alunos/{id}/diario-pedagogico` | Salva diário pedagógico. |
| `PUT` | `/alunos/{id}/hora-flexivel` | Toggle de cobrança flexível. |

### Tatame (`routers/tatame.py`) — tag: Tatame
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/tatame/ativos` | Alunos disponíveis (Ativo/Experimental). Inclui sessão em andamento. |
| `POST` | `/sessao/start` | Inicia sessão (cronômetro). |
| `POST` | `/sessao/stop` | Encerra sessão: calcula custo pela hierarquia de cobrança + registra presença. |

### Presença (`routers/presenca.py`) — tag: Presença
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/presenca/diaria` | Chamada do dia (sem Inativos). |
| `POST` | `/presenca/bulk` | Registro em lote. |

### Pagamentos (`routers/pagamentos.py`) — tag: Pagamentos
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/pagamentos/receber` | Recebe pagamento com quitação em cascata (taxa de admissão → sessões mais antigas). |

### Encerramento (`routers/encerramento.py`) — tag: Encerramento de Matrícula
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/alunos/{id}/encerrar` | Encerramento definitivo: gera dossiê PDF, agenda expurgo em 30 dias. |
| `GET` | `/encerramentos` | Lista matrículas em janela de retenção. |
| `GET` | `/alunos/{id}/dossie` | Download do dossiê PDF. |
| `POST` | `/alunos/{id}/revogar-encerramento` | Revoga dentro dos 30 dias. |

### Turmas (`routers/turmas.py`) — tag: Turmas
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/turmas` | Cria turma (com vínculos opcionais). |
| `GET` | `/turmas` | Lista turmas ativas. |
| `GET` | `/turmas/{id}` | Detalha turma com alunos (inclui graduação, status, restrição médica). |
| `PUT` | `/turmas/{id}` | Edita turma. |
| `POST` | `/turmas/{id}/alunos` | Vincula aluno (matriculado/ocorrente). |
| `DELETE` | `/turmas/{id}/alunos/{id_aluno}` | Desvincula aluno. |
| `DELETE` | `/turmas/{id}` | Desativa turma (soft). |

### Calendário / Ocorrências (`routers/ocorrencias.py`) — tag: Calendário / Ocorrências
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/turmas/{id}/ocorrencias/gerar` | Gera ocorrências da RRULE no intervalo (idempotente). |
| `GET` | `/ocorrencias` | Lista por período (`?inicio=&fim=`). |
| `GET` | `/calendario/dia/{dia}` | Detalhe do dia com participantes e duração. |
| `POST` | `/ocorrencias/avulsa` | Cria ocorrência fora da recorrência. |
| `PUT` | `/ocorrencias/{id}` | Edita (move data, muda estado, etc.). |
| `POST` | `/ocorrencias/{id}/cancelar` | Marca como `cancelada` (sai do cálculo financeiro). |
| `POST` | `/ocorrencias/{id}/presenca` | Marca presença/ausência por aluno. |
| `PUT` | `/ocorrencias/{id}/duracao` | Registra duração real (validação do professor). |
| `DELETE` | `/ocorrencias/{id}` | Exclui ocorrência. |

### Financeiro (`routers/financeiro.py`) — tag: Financeiro
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/financeiro/{id}/conta` | Saldo (em aberto / crédito / líquido) + extrato de lançamentos. |
| `GET` | `/financeiro/{id}/mensalidade/previsao` | Prévia do valor pelo calendário (sem criar débito). |
| `POST` | `/financeiro/{id}/mensalidade/gerar` | Materializa o débito do mês (idempotente por `mes_referencia`). |
| `POST` | `/financeiro/{id}/pagar` | Lança crédito e abate débitos mais antigos. |
| `POST` | `/financeiro/abono` | Abono de falta justificada (só mensalistas). |

### Anamnese (`routers/anamnese.py`) — tag: Anamnese
| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/anamnese/{id_aluno}` | Salva nova versão (desativa anterior, sincroniza legado). |
| `GET` | `/anamnese/{id_aluno}` | Anamnese ativa + card de alerta crítico + status de validade. |
| `GET` | `/anamnese/{id_aluno}/historico` | Todas as versões (histórico preservado). |

### Auditoria (`routers/auditoria.py`) — tag: Auditoria
| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/auditoria` | Lista eventos (`?categoria=geral|sensivel`). Aplica retenção lazy. |
| `GET` | `/auditoria/aluno/{id_aluno}` | Histórico de todos os eventos de um aluno. |

---

## 5. Regras de negócio 100% implementadas no MVP

### Cobrança por sessão de tatame
- **Hora flexível:** `horas × valor_base`
- **Mensalidade:** `(horas − 3) × valor_base` — franquia de 3h, nunca negativo
- **Intensivão:** `horas × (valor_base × 1.5)`
- **Horas Livres:** `horas × valor_base`
- Presença automática ao encerrar sessão.

### Trava automática de inadimplência
- Apenas plano `Mensalidade`.
- `hoje > dia_vencimento + 5 dias` → status `Trancado` + `[TRAVA AUTOMÁTICA]` na observação.
- `[ACORDO]` na observação → bypass total.
- Sessão aberta encerrada imediatamente ao trancar.
- Avaliação lazy (nas rotas) + job diário APScheduler.

### Mensalidade pelo calendário (conta corrente)
- Valor = `Σ (valor_base_da_turma × horas_previstas_da_ocorrência)` do mês.
- Apenas ocorrências `prevista`/`realizada` contam; `cancelada` sai da conta.
- Falta do aluno **não** altera o valor.
- Geração idempotente por `mes_referencia`.
- Crédito abate débito na geração e no pagamento.

### Turmas e calendário
- Turmas com recorrência RRULE (qualquer padrão iCalendar).
- Ocorrências geradas automaticamente, idempotente.
- Aluno `matriculado` (cobrado) ou `ocorrente` (participa, opcionalmente gratuito).
- Aluno de Legado em turma Dojo como ocorrente → gratuito automático.

### Progressão marcial
- **Gakusei** (Ashigaru/Kyu): meta 5 meses.
- **Bushi/Dan**: meta 12 meses.
- API retorna sempre `meses_faltantes`.

### Anamnese versionada
- Validade de 6 ou 12 meses; alerta `vencida`/`vence_em_breve`/`ok`.
- Versões antigas preservadas como histórico.
- Card de alerta crítico extraído das condições clinicamente relevantes.
- Sincroniza `Aluno.restricao_medica` (coexistência com o legado).

### Ciclo de vida da matrícula
- **Suspensão** (soft/reversível): `status_atividade = Inativo`.
- **Encerramento** (definitivo): dossiê PDF → janela 30 dias → expurgo Hard Delete (LGPD).
- Revogação possível durante a janela.

### Auditoria de segurança
- Fila **Geral**: máx. 50 entradas, retenção 60 dias.
- **Sensíveis**: isoladas, sem poda.
- Visão por aluno: transversal.
- Log **sobrevive ao expurgo** do aluno (sem FK).

### Segurança (S1–S3)
- **S1:** fail-safe de `JWT_SECRET` padrão em produção (recusa subir).
- **S2:** política de força de senha (min 10 chars, misturado); flag `precisa_trocar_senha`; endpoint de troca; modal bloqueante no front.
- **S3:** rate limiting no login (5 falhas/5 min → bloqueio 15 min por usuário+IP); bloqueio auditado.

### Validações de negócio
- Menor de 18 anos exige `nome_pai` e `nome_mae`.
- `dia_vencimento` só existe para plano `Mensalidade`.
- Alunos `Trancado`/`Inativo`/`Encerrado` não aparecem no tatame.

---

## 6. Cadeia de migrations Alembic

```
639d4d737621  esquema inicial
      ↓
bdf6715ed4b1  corrige horas_franquia (4 → 3)
      ↓
c1a2b3d4e5f6  encerramento de matrícula (dossiê + expurgo)
      ↓
d2b3c4e5f6a7  turmas
      ↓
e3c4d5f6a7b8  ocorrências de aula
      ↓
f4d5e6a7b8c9  financeiro (lançamentos + abonos_falta)
      ↓
a7b8c9d0e1f2  anamnese versionada
      ↓
b8c9d0e1f2a3  auditoria (registros_auditoria)
      ↓
c9d0e1f2a3b4  usuario.precisa_trocar_senha  ← HEAD
```

---

## 7. Suíte de testes

| Arquivo | O que cobre |
|---|---|
| `test_smoke.py` | Import e startup da aplicação |
| `test_auth.py` | Login, JWT, 401/403 |
| `test_cobranca.py` | Hierarquia de cobrança por sessão |
| `test_trava.py` | Trava automática de inadimplência |
| `test_soft_delete.py` | Soft delete, sessão encerrada ao inativar |
| `test_valor_base.py` | Atualização de valor base |
| `test_encerramento.py` | Encerramento, dossiê PDF, revogação, expurgo |
| `test_turmas.py` | CRUD de turmas, vínculos, ocorrente gratuito |
| `test_ocorrencias.py` | RRULE, geração idempotente, presença, cancelamento |
| `test_financeiro.py` | Conta corrente, mensalidade pelo calendário, crédito |
| `test_anamnese.py` | Versionamento, validade, card de alerta, legado |
| `test_auditoria.py` | Categorias, retenção, poda, filtros |
| `test_seguranca.py` | S1 fail-safe, S2 política de senha, S3 rate limit |
| **Total** | **121 testes, todos verdes** |

---

## 8. Como rodar localmente

```powershell
# Terminal 1 — Back-end
cd "C:\dev\Kiron YnK\backend"
pip install -r requirements.txt
alembic stamp b8c9d0e1f2a3    # só se o banco foi criado antes das migrations
alembic upgrade head           # aplica migrations pendentes
python create_admin.py         # idempotente
uvicorn main:app --reload      # http://localhost:8000  (Swagger em /docs)

# Terminal 2 — Front-end
cd "C:\dev\Kiron YnK\frontend"
npm install
npm start                      # http://localhost:4200
```

**Login:** credenciais em `backend/create_admin.py` (variável `USUARIOS_INICIAIS`).
No primeiro login, o sistema exige a troca da senha (modal bloqueante — S2).

> Se o PowerShell bloquear o `npm`: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`
