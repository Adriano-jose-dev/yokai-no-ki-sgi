# Design — Estabilização e Produção do SGI-YKR

## Visão Geral

Este design descreve como estabilizar o MVP (Fase B) e prepará-lo para nuvem
(Fase A), mantendo a stack atual (FastAPI + SQLAlchemy + Angular/Tailwind) e as
regras do steering `regras-negocio-ykr.md` como fonte da verdade.

O trabalho é incremental e preserva o comportamento correto já existente. Nenhuma
regra de negócio muda de valor; corrigimos onde o código diverge do steering
(ex.: franquia de horas) e removemos duplicações e valores mágicos.

### Estado atual (resumo do diagnóstico)

- Back-end monolítico em um único `main.py` (~950 linhas): models, schemas
  Pydantic e rotas juntos.
- Regra de trava de inadimplência **duplicada** em `editar_contrato` e
  `obter_progresso`.
- Cálculo da Mensalidade usa `3.0` hard-coded, enquanto o model `Contrato` tem
  `horas_franquia = 4` (divergência com o steering, que exige 3h).
- Front-end chama `http://127.0.0.1:8000` hard-coded em todos os componentes.
- Rota `PUT /alunos/{id}/valor-base` é chamada pelo front mas não existe no back.
- Sem autenticação, CORS `*`, sem migrations, sem agendador.

### Princípios de design

- **Fonte única da verdade para regras:** cada regra de negócio vive em uma
  função só.
- **Sem valores mágicos:** parâmetros de regra (franquia) vêm do banco.
- **Configuração por ambiente:** nada de URLs, segredos ou strings de conexão no
  código.
- **Mudanças reversíveis e verificáveis:** cada correção deve ser testável.

---

## Fase B — Estabilização

### B1. Franquia de horas dinâmica (Req. 1)

**Mudança no model `Contrato`:** alterar o default de `horas_franquia` de `4`
para `3`.

**Mudança em `finalizar_sessao`:** substituir o `3.0` fixo pelo campo do
contrato. A lógica de cálculo passa a ser:

```
franquia = contrato.horas_franquia            # padrão 3
if aluno.hora_flexivel:
    custo = horas_decimais * valor_base
elif plano == "Mensalidade":
    excedente = max(0.0, horas_decimais - franquia)
    custo = excedente * valor_base
elif plano == "Intensivão":
    custo = horas_decimais * (valor_base * 1.5)
else:  # Horas Livres
    custo = horas_decimais * valor_base
custo = max(0.0, custo - desconto)
```

**Dados legados:** contratos com `horas_franquia = 4` são corrigidos para `3` por
script (Fase B) e formalizado como migration na Fase A (Req. 9).

### B2. Regra de trava unificada (Req. 2)

Extrair uma função única, por exemplo:

```
def avaliar_trava_inadimplencia(db, aluno, contrato, hoje) -> bool:
    # retorna atraso_critico (bool)
    # aplica/reverte status Trancado, prefixo [TRAVA AUTOMÁTICA],
    # encerra sessão aberta, respeita [ACORDO].
```

Regras consolidadas dentro dela (do steering):
- Aplica-se apenas a `Mensalidade`.
- Atraso = `hoje > dia_vencimento + 5 dias`.
- `[ACORDO]` em `observacao_financeira` → bypass total.
- Ao trancar: status `Trancado`, prefixo `[TRAVA AUTOMÁTICA]`, encerrar sessão
  aberta com nota de sistema.
- Se voltou a ficar em dia e a trava foi automática, reverter para `Ativo` e
  limpar o prefixo.

`obter_progresso` e `editar_contrato` passam a **chamar** essa função em vez de
reimplementá-la. O comportamento correto atual é preservado (Req. 2.7).

> Observação de robustez: a construção da data de vencimento deve tratar meses
> com menos dias (ex.: vencimento 31 em fevereiro), reaproveitando o fallback com
> `calendar.monthrange` já presente no código.

### B3. Rota de valor base (Req. 3)

Criar o endpoint que o front já invoca:

- **Contrato:** `PUT /alunos/{id_matricula}/valor-base`
- **Corpo:** `{ "valor_base": number }` (schema `AtualizarValorBaseRequest`, que
  já existe sem rota).
- **Comportamento:** localizar contrato do aluno, atualizar `valor_base`,
  commit. Retornar `404` se aluno/contrato não existir.

### B4. Soft Delete formalizado (Req. 4)

- Adicionar endpoint `PUT /alunos/{id_matricula}/desativar` que seta
  `status_atividade = "Inativo"` e encerra sessão aberta (reaproveitando a mesma
  lógica de encerramento usada em `alterar_status`).
- Confirmar que as listagens operacionais (`/tatame/ativos`, `/presenca/diaria`)
  filtram `Inativo` — a chamada diária já filtra; o Tatame já filtra por
  `Ativo`/`Aula Experimental`, o que naturalmente exclui `Inativo`.
- Nenhuma rota de DELETE físico será adicionada.

### B5. Environments no Angular (Req. 5)

- Definir `environment.ts` (dev) e `environment.prod.ts` (prod) com
  `apiUrl`.
- Criar um `ApiService` (ou ao menos uma constante central) que exponha
  `apiUrl`, e refatorar `daily-panel`, `admin-detail`, `matricula-form` e
  `presenca-panel` para consumir essa fonte em vez da string literal.
- Preferência: centralizar as chamadas HTTP em um `ApiService` para reduzir
  repetição e facilitar o envio do token JWT depois (Fase A).

### Refatoração estrutural do back-end (suporte às fases)

Para viabilizar as mudanças sem inflar ainda mais o `main.py`, propõe-se separar
gradualmente:

```
YnkBD/
  main.py            # app FastAPI + inclusão de routers
  database.py        # engine, SessionLocal, get_db, Base
  models.py          # models SQLAlchemy
  schemas.py         # modelos Pydantic
  business/
    trava.py         # avaliar_trava_inadimplencia (regra única)
    cobranca.py      # cálculo de custo de sessão
  routers/
    alunos.py, tatame.py, presenca.py, pagamentos.py, auth.py
  config.py          # leitura de variáveis de ambiente
```

Esta separação é opcional para a Fase B mínima, mas recomendada porque a Fase A
(auth, config, agendador) fica muito mais limpa. As tarefas marcarão o que é
essencial vs. recomendado.

---

## Fase A — Produção

### A1. Autenticação JWT extensível (Req. 6)

- Nova tabela `Usuario`: `id`, `username`, `senha_hash`, `role` (default
  `admin`), `ativo`.
- Hash de senha com `passlib` (bcrypt).
- Endpoint `POST /auth/login` → valida credenciais, retorna
  `{ access_token, token_type }`. O JWT carrega `sub` (username) e `role`.
- Dependência `get_usuario_atual` que valida o token e injeta o usuário.
- **Extensibilidade para `Sensei`:** o `role` já viaja no token. Rotas do Tatame
  poderão, no futuro, aceitar `admin` ou `sensei`; as demais, apenas `admin`. Na
  Fase A todas as rotas exigem apenas token válido (papel único `admin`), mas a
  verificação de papel fica encapsulada em uma dependência
  `requer_papel(*roles)` já pronta para uso.
- Segredo do JWT e expiração vêm de variável de ambiente.

**Front-end:** `AuthService` guarda o token (localStorage), um `HttpInterceptor`
injeta `Authorization: Bearer <token>`, e um guard redireciona para login quando
não autenticado. Tela de login simples.

### A2. CORS restrito (Req. 7)

- Ler `CORS_ORIGINS` (lista separada por vírgula) da configuração.
- Em dev, incluir a origem local do Angular (`http://localhost:4200`).
- Remover o `["*"]` fixo.

### A3. Banco por ambiente (Req. 8)

- `config.py` lê `DATABASE_URL`. Sem ela, cai em `sqlite:///./yokai.db`.
- `connect_args={"check_same_thread": False}` aplicado apenas quando a URL é
  SQLite.
- PostgreSQL via `psycopg2-binary` (ou `psycopg`).

### A4. Migrations com Alembic (Req. 9)

- Inicializar Alembic apontando para a `Base` e a `DATABASE_URL` da config.
- Migration inicial refletindo o esquema atual (alunos, contratos, sessoes,
  pagamentos, presencas) + tabela `usuarios`.
- Migration de dados: `UPDATE contratos SET horas_franquia = 3 WHERE
  horas_franquia = 4`.
- Produção passa a rodar `alembic upgrade head` em vez de `create_all`.

### A5. Agendador da trava (Req. 10)

- `APScheduler` (BackgroundScheduler) iniciado no startup do FastAPI.
- Job diário à meia-noite: itera contratos `Mensalidade` e chama
  `avaliar_trava_inadimplencia` (a MESMA função da Fase B — sem duplicação).
- A avaliação lazy nas rotas permanece como rede de segurança.
- Cuidado com concorrência: o job abre sua própria `Session` e faz commit por
  aluno ou em lote com tratamento de erro.

### A6. Deploy de baixo custo (Req. 11)

Arquitetura de referência (todas com free tier no momento da escrita; confirmar
limites antes de publicar):

| Camada | Opção sugerida | Observação |
|---|---|---|
| Back-end FastAPI | Render (Web Service) ou Railway | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Banco PostgreSQL | Render Postgres ou Neon | Neon tem free tier generoso |
| Front-end Angular | Vercel ou Netlify | build estático `ng build` |

Artefatos a produzir:
- `requirements.txt` no back-end (fastapi, uvicorn, sqlalchemy, alembic,
  passlib[bcrypt], python-jose ou pyjwt, apscheduler, psycopg2-binary,
  python-dotenv).
- `.env.example` documentando `DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MIN`,
  `CORS_ORIGINS`, credenciais do usuário admin inicial.
- README de deploy com a ordem: provisionar Postgres → configurar variáveis →
  `alembic upgrade head` → subir back-end → publicar front apontando `apiUrl`
  para a URL do back.

> Nota de compliance: as opções e limites de free tier de Render, Railway, Neon,
> Vercel e Netlify mudam com frequência. A documentação indicará as opções, mas
> os limites atuais devem ser confirmados nas páginas oficiais no momento do
> deploy.

---

## Modelos de Dados (mudanças)

- `Contrato.horas_franquia`: default `4` → `3`.
- Nova entidade `Usuario` (auth): `id`, `username` (único), `senha_hash`,
  `role` (default `"admin"`), `ativo` (default `True`).
- Demais models permanecem; nenhum campo é removido para preservar histórico
  (Soft Delete).

## Tratamento de Erros

- Rotas que buscam aluno/contrato inexistente retornam `404` (padronizar; hoje
  parte do código assume que o registro existe e pode lançar `AttributeError`).
- Rotas protegidas sem token: `401`.
- Falha de papel (futuro `Sensei`): `403`.

## Estratégia de Testes

- **Regras de negócio (prioritário):** testes unitários para
  `avaliar_trava_inadimplencia` e para o cálculo de custo de sessão cobrindo:
  Mensalidade dentro/fora da franquia, Intensivão, Horas Livres, hora flexível,
  `[ACORDO]`, atraso com/sem sessão aberta.
- **Rotas:** testes de integração com `TestClient` e SQLite em memória para
  login, valor-base, desativar, iniciar/finalizar sessão.
- **Migrations:** validar `alembic upgrade head` em banco limpo e a correção de
  `horas_franquia`.
- Sem framework de teste no back-end hoje; será adicionado `pytest`.

## Sequenciamento entre fases

Fase B é pré-requisito da Fase A: a função única de trava (B2) é reutilizada pelo
agendador (A5); os environments (B5) são pré-requisito para o interceptor de
auth (A1). Por isso as tarefas seguem a ordem B → A.
