# Plano de Implementação — Estabilização e Produção do SGI-YKR

> Execução em ordem. Fase B (estabilização) precede Fase A (produção), pois A
> reutiliza artefatos de B. Cada tarefa referencia os requisitos que atende.

## Fase B — Estabilização

- [x] 1. Preparar ambiente de testes do back-end
  - Adicionar `pytest` e configurar um `conftest.py` com fixture de banco SQLite
    em memória e `TestClient`.
  - Criar `requirements.txt` inicial (mesmo que mínimo) para reproduzir o setup.
  - _Requisitos: base de verificação para todas as tarefas seguintes_

- [x] 2. Corrigir a franquia de horas da Mensalidade
  - [x] 2.1 Alterar o default de `Contrato.horas_franquia` de `4` para `3` no model.
    - _Requisitos: 1.1_
  - [x] 2.2 Refatorar `finalizar_sessao` para consumir `contrato.horas_franquia`
    em vez do `3.0` fixo, garantindo custo nunca negativo.
    - _Requisitos: 1.2, 1.3, 1.4_
  - [x] 2.3 Escrever script de correção de dados para contratos legados
    (`horas_franquia = 4` → `3`).
    - _Requisitos: 1.5_
  - [x] 2.4 Testes unitários do cálculo de custo (Mensalidade dentro/fora da
    franquia, Intensivão, Horas Livres, hora flexível, desconto).
    - _Requisitos: 1.2, 1.3_

- [x] 3. Unificar a regra de trava de inadimplência
  - [x] 3.1 Criar `business/trava.py` com `avaliar_trava_inadimplencia(db, aluno,
    contrato, hoje) -> bool`, consolidando toda a regra do steering (atraso,
    `[ACORDO]`, trancar, prefixo `[TRAVA AUTOMÁTICA]`, encerrar sessão aberta,
    reverter quando em dia).
    - _Requisitos: 2.1, 2.4, 2.5, 2.6_
  - [x] 3.2 Substituir a lógica duplicada em `obter_progresso` por chamada à
    função única.
    - _Requisitos: 2.2, 2.7_
  - [x] 3.3 Substituir a lógica duplicada em `editar_contrato` por chamada à
    função única.
    - _Requisitos: 2.3, 2.7_
  - [x] 3.4 Testes unitários da trava cobrindo atraso com/sem `[ACORDO]`,
    reversão ao ficar em dia, encerramento de sessão aberta e vencimento em mês
    curto (ex.: dia 31 em fevereiro).
    - _Requisitos: 2.4, 2.5, 2.6, 2.7_

- [x] 4. Criar a rota de atualização de valor base
  - Implementar `PUT /alunos/{id_matricula}/valor-base` usando o schema
    `AtualizarValorBaseRequest`, com `404` para aluno/contrato inexistente.
  - Teste de integração cobrindo sucesso e 404.
  - _Requisitos: 3.1, 3.2, 3.3, 3.4_

- [x] 5. Formalizar o Soft Delete
  - [x] 5.1 Implementar `PUT /alunos/{id_matricula}/desativar` (status →
    `Inativo`, encerrando sessão aberta), reutilizando a lógica de encerramento.
    - _Requisitos: 4.2, 4.3, 4.5_
  - [x] 5.2 Confirmar (e ajustar se necessário) que `/tatame/ativos` e
    `/presenca/diaria` omitem alunos `Inativo`; garantir ausência de qualquer
    hard delete.
    - _Requisitos: 4.1, 4.4_
  - [x] 5.3 Teste de integração: desativar aluno com sessão aberta e verificar
    encerramento + preservação de histórico.
    - _Requisitos: 4.3, 4.5_

- [x] 6. Centralizar a URL da API no front-end
  - [x] 6.1 Definir `apiUrl` em `environment.ts` (dev) e `environment.prod.ts`
    (prod) e criar um `ApiService` central.
    - _Requisitos: 5.2, 5.3, 5.4_
  - [x] 6.2 Refatorar `daily-panel`, `admin-detail`, `matricula-form` e
    `presenca-panel` para usar o `ApiService`/`apiUrl`, removendo todas as
    strings `http://127.0.0.1:8000`.
    - _Requisitos: 5.1, 5.5_
  - [x] 6.3 Validar build de dev e conferir que nenhuma URL literal permanece.
    - _Requisitos: 5.1_

- [x] 7. (Recomendado) Modularizar o back-end
  - Separar `database.py`, `models.py`, `schemas.py`, `routers/` e `business/`,
    mantendo o comportamento. Passo de suporte que facilita a Fase A.
  - Rodar a suíte de testes após a separação para garantir zero regressão.
  - _Requisitos: suporte a 2, 6, 8, 10_

## Fase A — Produção

- [x] 8. Configuração por ambiente
  - Criar `config.py` lendo `DATABASE_URL`, `JWT_SECRET`, `JWT_EXPIRE_MIN`,
    `CORS_ORIGINS` via `python-dotenv`; criar `.env.example`.
  - Aplicar `DATABASE_URL` no engine (SQLite como fallback; `check_same_thread`
    só para SQLite).
  - _Requisitos: 8.1, 8.2, 8.3, 8.4_

- [x] 9. Restringir CORS por configuração
  - Trocar `allow_origins=["*"]` por origens vindas de `CORS_ORIGINS`; manter
    origem local do Angular em dev.
  - _Requisitos: 7.1, 7.2, 7.3_

- [x] 10. Autenticação JWT (back-end)
  - [x] 10.1 Criar model `Usuario` (`username`, `senha_hash`, `role` default
    `admin`, `ativo`) e schema de login.
    - _Requisitos: 6.4, 6.5_
  - [x] 10.2 Implementar `POST /auth/login` (hash bcrypt via passlib, emissão de
    JWT com `sub` e `role`, expiração da config).
    - _Requisitos: 6.1, 6.4, 6.6_
  - [x] 10.3 Criar dependências `get_usuario_atual` e `requer_papel(*roles)` e
    proteger as rotas existentes (papel único `admin` por ora).
    - _Requisitos: 6.2, 6.3, 6.5_
  - [x] 10.4 Script para criar o usuário admin inicial a partir de variáveis de
    ambiente.
    - _Requisitos: 6.4_
  - [x] 10.5 Testes de auth: login válido/ inválido, acesso sem token (401), com
    token (200).
    - _Requisitos: 6.1, 6.2, 6.3, 6.6_

- [x] 11. Autenticação (front-end)
  - Criar tela de login, `AuthService` (guardar token), `HttpInterceptor`
    (injeta `Authorization: Bearer`) e guard de rota.
  - _Requisitos: 6.7_

- [x] 12. Migrations com Alembic
  - [x] 12.1 Inicializar Alembic apontando para `Base` e `DATABASE_URL`.
    - _Requisitos: 9.1, 9.4_
  - [x] 12.2 Gerar migration inicial do esquema atual + tabela `usuarios`.
    - _Requisitos: 9.2_
  - [x] 12.3 Criar migration de dados `horas_franquia = 4 → 3`.
    - _Requisitos: 9.3_
  - [x] 12.4 Substituir `create_all` por `alembic upgrade head` no fluxo de
    produção.
    - _Requisitos: 9.4_

- [x] 13. Agendador diário da trava
  - Adicionar APScheduler no startup, com job à meia-noite que varre contratos
    `Mensalidade` e chama `avaliar_trava_inadimplencia` (função única da tarefa
    3); manter avaliação lazy como rede de segurança.
  - Teste do job simulando alunos em atraso (com e sem `[ACORDO]`) e com sessão
    aberta.
  - _Requisitos: 10.1, 10.2, 10.3, 10.4_

- [x] 14. Empacotamento e documentação de deploy
  - Finalizar `requirements.txt`, documentar variáveis em `.env.example`, definir
    comando de start ASGI e build de produção do Angular.
  - Escrever README de deploy (ordem: Postgres → variáveis → `alembic upgrade
    head` → back-end → front) com opções de baixo custo (confirmar limites de
    free tier nas páginas oficiais no momento do deploy).
  - _Requisitos: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 15. Enriquecer a documentação de API (Swagger)
  - Adicionar `summary`/`description` e `tags` (alunos, tatame, presença,
    pagamentos, auth) aos endpoints; conferir schemas de entrada/saída.
  - Documentar no README como acessar `/docs`.
  - _Requisitos: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 16. Configurar CI com GitHub Actions
  - Criar workflow que instala dependências do `requirements.txt` e roda a suíte
    `pytest` a cada push e pull request; opcionalmente validar o build do
    Angular.
  - Adicionar badge de status do CI no README.
  - _Requisitos: 13.1, 13.2, 13.3, 13.4, 13.5_
